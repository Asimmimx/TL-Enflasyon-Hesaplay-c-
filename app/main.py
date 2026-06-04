"""
TL Enflasyon Hesaplayıcı — FastAPI backend.

- Statik frontend'i (static/) servis eder.
- /api/data      : TÜFE + USD/TL verisini ve tarih aralığını döner.
- /api/calculate : Alım gücü hesaplaması yapar (TL + dolar bazında).
- /api/refresh   : EVDS'den veriyi zorla yeniler (cron/Task Scheduler için).
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import enag
from . import foreign_cpi
from . import ito
from . import minwage
from .evds import ASSETS, DataService, EVDSError

# Varlık -> "kendi" enflasyonu bölgesi (yabancı TÜFE). Altın hariç.
FOREIGN_CPI_REGION = {"usd": "us", "eur": "ea"}

load_dotenv()

API_KEY = os.getenv("EVDS_API_KEY", "")
TUFE_SERIES = os.getenv("EVDS_SERIES", "TP.FG.J0")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "43200"))

# Hız sınırı (rate limit) — IP başına dakikadaki istek sayısı. Bellek-içi, bağımlılıksız.
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
# X-Forwarded-For başlığına güvenilsin mi? (ters proxy/CDN arkasında çalışırken True yapın)
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

data_service = DataService(api_key=API_KEY, tufe_series=TUFE_SERIES, cache_ttl=CACHE_TTL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await data_service.ensure_loaded()
    except EVDSError as exc:
        print(f"[UYARI] Açılışta veri yüklenemedi: {exc}")
    yield


app = FastAPI(title="TL Enflasyon Hesaplayıcı", lifespan=lifespan)


# --------------------------------------------------------------------------- #
# Hız sınırı (rate limit) — bellek-içi kayan pencere (sliding window)
# --------------------------------------------------------------------------- #
# IP başına son 60 saniyedeki istek zaman damgalarını tutar; yeni dış bağımlılık yok.
# Tek uvicorn süreci/asyncio için yeterlidir (kontrol bloğunda await yok → kilit gerekmez).
_RATE_WINDOW = 60.0  # saniye
# Yol bazında dakikalık limitler. /api/refresh (cron) sıkı; /api/calculate kullanıcı limiti.
_RATE_LIMITS: dict[str, int] = {
    "/api/calculate": RATE_LIMIT_PER_MIN,
    "/api/data": max(RATE_LIMIT_PER_MIN * 2, 120),
    "/api/refresh": 5,
}
_rate_hits: dict[str, deque[float]] = defaultdict(deque)
_rate_last_sweep = 0.0


def _client_ip(request: Request) -> str:
    """İstemci IP'si. Proxy'ye güveniliyorsa X-Forwarded-For'un ilk parçası kullanılır."""
    if TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _sweep_stale(now: float) -> None:
    """Bir süredir istek göndermeyen IP girdilerini buda (bellek şişmesini önler)."""
    global _rate_last_sweep
    if now - _rate_last_sweep < _RATE_WINDOW:
        return
    _rate_last_sweep = now
    for key in [k for k, dq in _rate_hits.items() if not dq or now - dq[-1] > _RATE_WINDOW]:
        _rate_hits.pop(key, None)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """/api/ yolları için IP başına dakikalık istek sınırı uygular."""
    path = request.url.path
    limit = _RATE_LIMITS.get(path)
    if limit is not None:
        now = time.time()
        _sweep_stale(now)
        bucket = _rate_hits[f"{path}|{_client_ip(request)}"]
        while bucket and now - bucket[0] > _RATE_WINDOW:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = int(_RATE_WINDOW - (now - bucket[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Çok fazla istek gönderdiniz. Lütfen biraz bekleyip tekrar deneyin."},
                headers={"Retry-After": str(max(retry_after, 1))},
            )
        bucket.append(now)

    response = await call_next(request)
    # Statik içerik (HTML/JS/CSS) için tarayıcı her açılışta güncellik doğrulasın.
    # Böylece dosya değiştiğinde eski sürüm önbellekten gösterilmez (normal yenileme yeter).
    if not path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


class CalculateRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Hesaplanacak tutar (₺)")
    start_year: int = Field(..., ge=1900, le=2100)
    start_month: int = Field(..., ge=1, le=12)
    end_year: int = Field(..., ge=1900, le=2100)
    end_month: int = Field(..., ge=1, le=12)


def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


@app.get("/api/data")
async def get_data():
    """Frontend'in tarih seçicilerini doldurması için endeks verisini döner."""
    try:
        await data_service.ensure_loaded()
    except EVDSError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        **data_service.get_meta(),
        "values": data_service.get_tufe(),
        "enag": enag.coverage(),
        "ito": ito.coverage(),
    }


@app.post("/api/calculate")
async def calculate(req: CalculateRequest):
    """Sonuç = Tutar * (Bitiş TÜFE Endeksi / Başlangıç TÜFE Endeksi).
    Ayrıca dolar bazında karşılaştırma döner."""
    try:
        await data_service.ensure_loaded()
    except EVDSError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    tufe = data_service.get_tufe()
    assets = data_service.get_assets()
    start_key = _month_key(req.start_year, req.start_month)
    end_key = _month_key(req.end_year, req.end_month)

    start_index = tufe.get(start_key)
    end_index = tufe.get(end_key)

    missing = []
    if start_index is None:
        missing.append("başlangıç")
    if end_index is None:
        missing.append("bitiş")
    if missing:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Seçilen {' ve '.join(missing)} tarihi için henüz veri "
                "açıklanmamıştır. Lütfen farklı bir ay/yıl seçin."
            ),
        )

    result = req.amount * (end_index / start_index)
    change_pct = (result / req.amount - 1) * 100

    response = {
        "amount": req.amount,
        "result": round(result, 2),
        "start_index": start_index,
        "end_index": end_index,
        "start_key": start_key,
        "end_key": end_key,
        "change_pct": round(change_pct, 2),
        "multiplier": round(end_index / start_index, 4),
        "assets": {},
    }

    # Varlık bazında (dolar / euro / altın): tutarın başlangıçtaki ve enflasyona göre
    # güncellenen tutarın bitişteki "kaç birim/gram" karşılığı.
    for key, meta in ASSETS.items():
        prices = assets.get(key, {})
        p_start = prices.get(start_key)
        p_end = prices.get(end_key)
        if not (p_start and p_end):
            continue
        unit_start = req.amount / p_start
        unit_end = result / p_end
        entry = {
            "label": meta["label"],
            "symbol": meta["symbol"],
            "kind": meta["kind"],
            "unit_start": round(unit_start, 2),
            "unit_end": round(unit_end, 2),
            "price_start": round(p_start, 4),
            "price_end": round(p_end, 4),
            "change_pct": round((unit_end / unit_start - 1) * 100, 2),
        }
        # Para biriminin "kendi" enflasyonu (ABD TÜFE / Euro Bölgesi HICP) — yıllık, yaklaşık.
        region = FOREIGN_CPI_REGION.get(key)
        if region:
            cpi_chg = foreign_cpi.period_change(region, req.start_year, req.end_year)
            if cpi_chg is not None:
                entry["cpi_change_pct"] = round(cpi_chg, 2)
                entry["cpi_region"] = foreign_cpi.label(region)
        response["assets"][key] = entry

    # Reel enflasyon (ENAG, bağımsız) — yalnızca ENAG'ın kapsadığı dönemler için
    response["enag"] = None
    enag_start = enag.get_index(start_key)
    enag_end = enag.get_index(end_key)
    if enag_start and enag_end:
        enag_result = req.amount * (enag_end / enag_start)
        enag_change = (enag_result / req.amount - 1) * 100
        response["enag"] = {
            "result": round(enag_result, 2),
            "change_pct": round(enag_change, 2),
            "multiplier": round(enag_end / enag_start, 4),
            # TÜFE'ye kıyasla ENAG sonucu kaç kat? (reel/resmi farkı)
            "vs_tufe": round(enag_result / result, 2) if result else None,
            "verified": enag.is_verified(start_key) and enag.is_verified(end_key),
        }

    # İTO (İstanbul Ticaret Odası) — resmi TÜFE'ye İTO–TÜİK farkı uygulanır
    response["ito"] = None
    spread_start = ito.get_spread(start_key)
    spread_end = ito.get_spread(end_key)
    if spread_start and spread_end:
        spread_ratio = spread_end / spread_start
        ito_result = result * spread_ratio
        ito_change = (ito_result / req.amount - 1) * 100
        response["ito"] = {
            "result": round(ito_result, 2),
            "change_pct": round(ito_change, 2),
            "multiplier": round(ito_result / req.amount, 4),
            "vs_tufe": round(spread_ratio, 2),
        }

    # Asgari ücret karşılaştırması: tutar, başlangıç/bitiş yılının kaç net asgari ücreti?
    response["minwage"] = None
    wage_start = minwage.get(req.start_year)
    wage_end = minwage.get(req.end_year)
    if wage_start and wage_end:
        ratio_start = req.amount / wage_start
        ratio_end = result / wage_end
        response["minwage"] = {
            "wage_start": wage_start,
            "wage_end": wage_end,
            "ratio_start": round(ratio_start, 2),
            "ratio_end": round(ratio_end, 2),
            "change_pct": round((ratio_end / ratio_start - 1) * 100, 2),
        }

    # Zaman serisi (grafik): tutarın değerinin aylar boyunca seyri.
    response["series"] = _build_series(req.amount, tufe, start_key, end_key, start_index)

    return response


def _build_series(amount, tufe, start_key, end_key, start_index):
    """Grafik için aylık değer serileri üretir (TÜFE + ENAG + İTO).
    Her seri, ilgili ayda 'tutarın o günkü alım gücüne eşit TL miktarı'nı verir."""
    months = sorted(m for m in tufe if start_key <= m <= end_key)
    tufe_line = [round(amount * tufe[m] / start_index, 2) for m in months]

    def branch_line(idx_at):
        """Alt ölçümü, veriye sahip olduğu ilk aydan itibaren TÜFE çizgisinden dallandırır."""
        line, anchor_idx, anchor_val = [], None, None
        for i, m in enumerate(months):
            iv = idx_at(m)
            if iv is None:
                line.append(None)
                continue
            if anchor_idx is None:
                anchor_idx, anchor_val = iv, tufe_line[i]
            line.append(round(anchor_val * iv / anchor_idx, 2))
        return line

    def ito_idx(m):
        sp = ito.get_spread(m)
        tv = tufe.get(m)
        return tv * sp if (sp and tv) else None

    enag_line = branch_line(enag.get_index)
    ito_line = branch_line(ito_idx)

    return {
        "labels": months,
        "tufe": tufe_line,
        "enag": enag_line if any(v is not None for v in enag_line) else None,
        "ito": ito_line if any(v is not None for v in ito_line) else None,
    }


@app.post("/api/refresh")
async def refresh():
    """EVDS'den veriyi zorla yeniler (aylık cron job / Task Scheduler için)."""
    try:
        await data_service.ensure_loaded(force=True)
    except EVDSError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return JSONResponse({"status": "ok", **data_service.get_meta()})


# Statik frontend'i kökten servis et (API route'larından SONRA mount edilmeli).
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
