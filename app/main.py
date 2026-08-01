"""
TL Enflasyon Hesaplayıcı — FastAPI backend.

- Statik frontend'i (static/) servis eder.
- /api/data      : TÜFE endeksini, kapsamı, güncel enflasyon panosunu ve yıllık tabloyu döner.
- /api/calculate : Alım gücü hesaplaması yapar (TÜFE + ENAG + İTO, varlıklar, göstergeler).
- /api/refresh   : EVDS'den veriyi zorla yeniler (cron/Task Scheduler için).
"""

from __future__ import annotations

import math
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
from . import minwage
from .evds import ASSETS, INDICES, DataService, EVDSError

load_dotenv()

API_KEY = os.getenv("EVDS_API_KEY", "")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "43200"))

# Hız sınırı (rate limit) — IP başına dakikadaki istek sayısı. Bellek-içi, bağımlılıksız.
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
# X-Forwarded-For başlığına güvenilsin mi? (ters proxy/CDN arkasında çalışırken True yapın)
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Grafikte gönderilecek azami nokta sayısı (60 yıllık seri ~750 ay; yükü sınırlar).
MAX_SERIES_POINTS = 420
# Varlık fiyatı seçilen ayda yoksa en fazla kaç ay geriye bakılır (ör. altın 1-2 ay gecikir).
ASSET_LOOKBACK_MONTHS = 6

# Paradan altı sıfır atılması (5083 sayılı Kanun): 1 Ocak 2005'te 1.000.000 TL = 1 YTL.
# EVDS'nin tüm fiyat serileri YENİ TL cinsindendir; endeksler ise birimsizdir. Bu yüzden
# 2005 öncesi bir tarih seçildiğinde kullanıcının girdiği tutar "eski TL" kabul edilir ve
# hesaba girerken yeni TL'ye çevrilir; sonuç ise bitiş tarihinin para biriminde sunulur.
REDENOMINATION_KEY = "2005-01"
REDENOMINATION_FACTOR = 1_000_000

data_service = DataService(api_key=API_KEY, cache_ttl=CACHE_TTL)


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


# --------------------------------------------------------------------------- #
# Ay anahtarı ("YYYY-MM") yardımcıları
# --------------------------------------------------------------------------- #

def _month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _month_ordinal(key: str) -> int:
    """'YYYY-MM' -> mutlak ay sayısı (fark hesabı için)."""
    year, month = key.split("-")
    return int(year) * 12 + int(month) - 1


def _shift_months(key: str, delta: int) -> str:
    ordinal = _month_ordinal(key) + delta
    return f"{ordinal // 12:04d}-{ordinal % 12 + 1:02d}"


def _pct(index: dict[str, float], start_key: str, end_key: str):
    """İki ay arası yüzde değişim (endeks tabanından bağımsız)."""
    start, end = index.get(start_key), index.get(end_key)
    if not start or not end:
        return None
    return round((end / start - 1) * 100, 2)


def _sig(value: float, digits: int = 9) -> float:
    """Anlamlı basamağa yuvarlar. Grafik serisi 0,001 ile 37.717 arasında değerler
    içerebildiği için sabit ondalık yuvarlama (round(x, 2)) küçük değerleri sıfırlar."""
    if not value:
        return 0.0
    exponent = math.floor(math.log10(abs(value)))
    return round(value, max(0, digits - 1 - exponent))


def _is_old_lira(key: str) -> bool:
    """Bu ay, paradan altı sıfır atılmadan önceki (eski TL) döneme mi ait?"""
    return key < REDENOMINATION_KEY


def _to_try(value: float, key: str) -> float:
    """O ayın para birimindeki tutarı bugünkü TL'ye çevirir (eski TL ise ÷ 1.000.000)."""
    return value / REDENOMINATION_FACTOR if _is_old_lira(key) else value


def _from_try(value: float, key: str) -> float:
    """Bugünkü TL cinsinden tutarı, o ayın para birimine çevirir (_to_try'ın tersi)."""
    return value * REDENOMINATION_FACTOR if _is_old_lira(key) else value


def _price_at(prices: dict[str, float], key: str):
    """Seçilen aydaki fiyat; o ay yoksa en fazla ASSET_LOOKBACK_MONTHS geriye bakar.

    Bazı seriler (altın, Cumhuriyet altını) TÜFE'den 1-2 ay geriden gelir; bu yüzden
    en yakın önceki ay kullanılır. Hangi ayın kullanıldığı yanıtta belirtilir.
    """
    if key in prices:
        return prices[key], key
    earlier = [m for m in prices if m < key]
    if not earlier:
        return None, None
    nearest = max(earlier)
    if _month_ordinal(key) - _month_ordinal(nearest) > ASSET_LOOKBACK_MONTHS:
        return None, None
    return prices[nearest], nearest


# --------------------------------------------------------------------------- #
# Güncel durum panosu + yıllık tablo
# --------------------------------------------------------------------------- #

def _measure_snapshot(key: str, label: str, index: dict[str, float], official: bool,
                      hint: str | None = None) -> dict | None:
    """Bir endeksin en güncel ayı için aylık ve 12 aylık değişimini döner."""
    if not index:
        return None
    last = max(index)
    return {
        "key": key,
        "label": label,
        "official": official,
        "hint": hint,
        "month": last,
        "monthly": _pct(index, _shift_months(last, -1), last),
        "annual": _pct(index, _shift_months(last, -12), last),
    }


def _yearly_table(tufe: dict[str, float], ito: dict[str, float]) -> list[dict]:
    """Yıl sonu (Aralık→Aralık) enflasyon oranları. Devam eden yıl 'partial' işaretlenir."""
    if not tufe:
        return []
    enag_index = enag.index()
    last_month = max(tufe)
    last_year = int(last_month[:4])
    first_year = int(min(tufe)[:4]) + 1

    rows: list[dict] = []
    for year in range(first_year, last_year + 1):
        prev_dec = f"{year - 1:04d}-12"
        end = f"{year:04d}-12"
        partial = False
        if end not in tufe:
            candidates = [m for m in tufe if m.startswith(f"{year:04d}-")]
            if not candidates:
                continue
            end = max(candidates)
            partial = True
        row = {
            "year": year,
            "partial": partial,
            "through": end if partial else None,
            "tufe": _pct(tufe, prev_dec, end),
            "enag": _pct(enag_index, prev_dec, end),
            "ito": _pct(ito, prev_dec, end),
        }
        if row["tufe"] is not None:
            rows.append(row)
    return rows


@app.get("/api/data")
async def get_data():
    """Frontend'in tarih seçicilerini, güncel panoyu ve yıllık tabloyu doldurması için veri."""
    try:
        await data_service.ensure_loaded()
    except EVDSError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    tufe = data_service.get_tufe()
    indices = data_service.get_indices()
    assets = data_service.get_assets()

    measures = [_measure_snapshot("tufe", "TÜFE", tufe, True, "TÜİK — Türkiye geneli")]
    measures.append(_measure_snapshot(
        "enag", "ENAG", enag.index(), False, "Enflasyon Araştırma Grubu — bağımsız"))
    for key, meta in INDICES.items():
        measures.append(_measure_snapshot(
            key, meta.get("short", meta["label"]), indices.get(key, {}), False, meta["hint"]))

    latest_assets = []
    for key, meta in ASSETS.items():
        prices = assets.get(key)
        if not prices:
            continue
        last = max(prices)
        latest_assets.append({
            "key": key, "label": meta["label"], "symbol": meta["symbol"],
            "kind": meta["kind"], "month": last, "price": round(prices[last], 4),
            "annual": _pct(prices, _shift_months(last, -12), last),
        })

    return {
        **data_service.get_meta(),
        "values": tufe,
        "enag": enag.coverage(),
        "minwage": minwage.coverage(),
        "foreign_cpi": {r: foreign_cpi.coverage(r) for r in ("us", "ea")},
        "latest": {
            "measures": [m for m in measures if m],
            "assets": latest_assets,
        },
        "yearly": _yearly_table(tufe, indices.get("ito", {})),
    }


@app.post("/api/calculate")
async def calculate(req: CalculateRequest):
    """Sonuç = Tutar * (Bitiş TÜFE Endeksi / Başlangıç TÜFE Endeksi).
    Ayrıca ENAG/İTO karşılaştırması, varlık bazında karşılıklar ve göstergeler döner."""
    try:
        await data_service.ensure_loaded()
    except EVDSError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    tufe = data_service.get_tufe()
    assets = data_service.get_assets()
    assets_usd = data_service.get_assets_usd()
    indices = data_service.get_indices()
    start_key = _month_key(req.start_year, req.start_month)
    end_key = _month_key(req.end_year, req.end_month)

    if start_key > end_key:
        raise HTTPException(
            status_code=400,
            detail="Başlangıç tarihi bitiş tarihinden sonra olamaz.",
        )

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

    multiplier = end_index / start_index
    # Hesap bugünkü TL üzerinden yapılır; sonuç bitiş tarihinin para birimine geri çevrilir.
    amount_try = _to_try(req.amount, start_key)
    result_try = amount_try * multiplier
    result = _from_try(result_try, end_key)
    change_pct = (multiplier - 1) * 100

    official_start = data_service.official_start()
    response = {
        "amount": req.amount,
        "result": round(result, 2),
        "start_index": start_index,
        "end_index": end_index,
        "start_key": start_key,
        "end_key": end_key,
        "change_pct": round(change_pct, 2),
        "multiplier": round(multiplier, 4),
        # 1982 öncesi TÜİK'in aylık TÜFE'si yok; o dönem İTO endeksiyle uzatıldı.
        "estimated_start": bool(official_start and start_key < official_start),
        "official_start": official_start,
        # Paradan altı sıfır atılması (2005): girilen/gösterilen tutar hangi para biriminde?
        "old_lira_start": _is_old_lira(start_key),
        "old_lira_end": _is_old_lira(end_key),
        "assets": {},
        "indicators": {},
    }

    # Varlık bazında (dolar / euro / altın / BIST / petrol): tutarın başlangıçtaki ve
    # enflasyona göre güncellenen tutarın bitişteki "kaç birim" karşılığı.
    for key, meta in ASSETS.items():
        prices = assets.get(key, {})
        p_start, m_start = _price_at(prices, start_key)
        p_end, m_end = _price_at(prices, end_key)
        if not (p_start and p_end):
            continue
        # EVDS fiyatları her zaman bugünkü TL cinsindendir → çevrilmiş tutarlarla böl.
        unit_start = amount_try / p_start
        unit_end = result_try / p_end
        entry = {
            "label": meta["label"],
            "symbol": meta["symbol"],
            "kind": meta["kind"],
            "unit_start": round(unit_start, 4),
            "unit_end": round(unit_end, 4),
            # Fiyatlar, ait oldukları ayın para biriminde gösterilir (2005 öncesi = eski TL);
            # böylece "1970'te 1 gr altın 19,80 TL" gibi tarihsel olarak doğru okunur.
            "price_start": round(_from_try(p_start, m_start), 4),
            "price_end": round(_from_try(p_end, m_end), 4),
            "price_start_key": m_start,
            "price_end_key": m_end,
            # Fiyat artışı her zaman bugünkü TL üzerinden (para birimi değişiminden arınmış).
            "price_change_pct": round((p_end / p_start - 1) * 100, 2),
            "change_pct": round((unit_end / unit_start - 1) * 100, 2),
        }
        # Para biriminin "kendi" enflasyonu (ABD TÜFE / Euro Bölgesi HICP) — yıllık, yaklaşık.
        region = meta.get("cpi_region")
        if region:
            cpi_chg = foreign_cpi.period_change(region, req.start_year, req.end_year)
            if cpi_chg is not None:
                entry["cpi_change_pct"] = round(cpi_chg, 2)
                entry["cpi_region"] = foreign_cpi.label(region)
        # Varlığın dolar cinsinden değer değişimi (altın: ons; Brent: varil) —
        # "TL mi eridi, varlık mı gerçekten değerlendi?" sorusunu ayırır.
        usd_prices = assets_usd.get(key)
        if usd_prices:
            u_start, _ = _price_at(usd_prices, start_key)
            u_end, _ = _price_at(usd_prices, end_key)
            if u_start and u_end:
                entry["usd_change_pct"] = round((u_end / u_start - 1) * 100, 2)
                entry["usd_unit"] = meta.get("usd_unit", meta["symbol"])
        response["assets"][key] = entry

    # Alternatif enflasyon ölçümleri: ENAG (bağımsız) ve İTO (İstanbul Ticaret Odası).
    def alt_measure(index: dict[str, float]) -> dict | None:
        i_start, i_end = index.get(start_key), index.get(end_key)
        if not (i_start and i_end):
            return None
        alt_multiplier = i_end / i_start
        alt_result = _from_try(amount_try * alt_multiplier, end_key)
        return {
            "result": round(alt_result, 2),
            "change_pct": round((alt_multiplier - 1) * 100, 2),
            "multiplier": round(alt_multiplier, 4),
            # TÜFE'ye kıyasla sonuç kaç kat? (alternatif/resmi farkı)
            "vs_tufe": round(alt_multiplier / multiplier, 2) if multiplier else None,
        }

    response["enag"] = alt_measure(enag.index())
    if response["enag"]:
        response["enag"]["verified"] = enag.is_verified(start_key) and enag.is_verified(end_key)

    ito_index = indices.get("ito", {})
    response["ito"] = alt_measure(ito_index)

    # Diğer göstergeler: dönem boyunca yüzde değişim (ÜFE, konut, İTO toptan eşya).
    for key, meta in INDICES.items():
        if key == "ito":
            continue
        change = _pct(indices.get(key, {}), start_key, end_key)
        if change is None:
            continue
        response["indicators"][key] = {
            "label": meta["label"],
            "hint": meta["hint"],
            "change_pct": round(change, 2),
        }

    # Asgari ücret karşılaştırması: tutar, başlangıç/bitiş yılının kaç net asgari ücreti?
    response["minwage"] = None
    wage_start = minwage.get(req.start_year)
    wage_end = minwage.get(req.end_year)
    if wage_start and wage_end:
        # Asgari ücret tablosu bugünkü TL cinsindendir → çevrilmiş tutarlarla oranla.
        ratio_start = amount_try / wage_start
        ratio_end = result_try / wage_end
        response["minwage"] = {
            "wage_start": wage_start,
            "wage_end": wage_end,
            "ratio_start": round(ratio_start, 2),
            "ratio_end": round(ratio_end, 2),
            "change_pct": round((ratio_end / ratio_start - 1) * 100, 2),
        }

    # Zaman serisi (grafik): tutarın değerinin aylar boyunca seyri.
    # Tüm çizgi, başlıktaki sonuçla aynı para biriminde (bitiş tarihininki) verilir;
    # böylece 2005'te paradan sıfır atılması grafikte yapay bir sıçrama yaratmaz.
    response["series"] = _build_series(
        _from_try(amount_try, end_key), tufe, ito_index, start_key, end_key, start_index)

    return response


def _build_series(amount, tufe, ito_index, start_key, end_key, start_index):
    """Grafik için aylık değer serileri üretir (TÜFE + ENAG + İTO).
    Her seri, ilgili ayda 'tutarın o günkü alım gücüne eşit TL miktarı'nı verir."""
    months = sorted(m for m in tufe if start_key <= m <= end_key)
    # Uzun dönemlerde (60 yıl ≈ 750 ay) noktaları seyrelt; ilk ve son ay hep kalır.
    if len(months) > MAX_SERIES_POINTS:
        step = len(months) // MAX_SERIES_POINTS + 1
        months = months[::step] + ([months[-1]] if (len(months) - 1) % step else [])
        months = sorted(set(months))

    tufe_line = [_sig(amount * tufe[m] / start_index) for m in months]

    def branch_line(index):
        """Alt ölçümü, veriye sahip olduğu ilk aydan itibaren TÜFE çizgisinden dallandırır."""
        line, anchor_idx, anchor_val = [], None, None
        for i, m in enumerate(months):
            iv = index.get(m)
            if iv is None:
                line.append(None)
                continue
            if anchor_idx is None:
                anchor_idx, anchor_val = iv, tufe_line[i]
            line.append(_sig(anchor_val * iv / anchor_idx))
        return line

    enag_line = branch_line(enag.index())
    ito_line = branch_line(ito_index)

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
