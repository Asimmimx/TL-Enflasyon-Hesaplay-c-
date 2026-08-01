"""
TCMB EVDS (Elektronik Veri Dağıtım Sistemi) istemcisi.

Aylık TÜFE, alternatif fiyat endeksleri (İTO, ÜFE, konut) ve varlık fiyatlarını
(dolar, euro, altın, BIST 100, Brent petrol) EVDS'den çeker, diske önbellekler
ve uygulamaya sade sözlükler olarak sunar.

EVDS hakkında:
  - Yeni servis adresi (2024+): https://evds3.tcmb.gov.tr/igmevdsms-dis
  - İstek biçimi: parametreler URL yoluna (path) gömülür; API anahtarı 'key'
    HTTP başlığı (header) ile gönderilir.
  - Örnek: .../igmevdsms-dis/series=TP.GENENDEKS.T1&startDate=01-01-1964&...&frequency=5

TÜFE ZİNCİRİ (ÖNEMLİ)
---------------------
TÜİK, Ocak 2026'da TÜFE'nin temel yılını 2003=100'den 2025=100'e güncelledi. Eski
`TP.FG.J0` serisi Ocak 2026'da durdu; yerine 2003=100 tabanını sürdüren
`TP.GENENDEKS.T1` yayımlanıyor. Ayrıca EVDS'de 2003 öncesine ait arşiv serileri var.
Bu üç seriyi tek bir kesintisiz endekste birleştiriyoruz (bkz. CPI_CHAIN):

    1964-01 … 1981-12  İTO İstanbul Ücretliler Geçinme Endeksi  (TÜİK dışı — tahmini)
    1982-01 … 2002-12  TÜİK TÜFE, 1978-79=100 (arşiv)
    2003-01 … bugün    TÜİK TÜFE, 2003=100

Zincirleme, iki serinin çakıştığı ilk ayda oran alınarak yapılır (standart
"chain-linking"). 1982 öncesi TÜİK'in aylık verisi yoktur; o dönem İTO'nun İstanbul
endeksiyle uzatılır ve `official: false` olarak işaretlenir — arayüzde bu dönem için
uyarı gösterilir.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx

EVDS_BASE_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
CACHE_FILE = Path(__file__).resolve().parent.parent / "cache" / "data_cache.json"

# Önbellek biçimi sürümü. Seri listesi/yapı değişince artırılır; eski önbellek yok sayılır.
CACHE_SCHEMA = 3

# EVDS frekans kodu: 5 = Aylık
_MONTHLY_FREQUENCY = 5
# Eş zamanlı EVDS isteği sınırı (servisi yormamak için).
_MAX_CONCURRENCY = 8
# Tüm serilerin çekilmesi için toplam süre bütçesi (saniye). Sunucusuz ortamlarda
# (Vercel vb.) istek süresi sınırlıdır; bütçe aşılırsa eldeki önbellekle devam edilir.
FETCH_BUDGET_SECONDS = float(os.getenv("EVDS_FETCH_TIMEOUT", "20"))
# Zincirin en eski ucu — buradan öncesi için veri yok.
_HISTORY_START = "01-01-1960"

# --------------------------------------------------------------------------- #
# TÜFE zinciri — eskiden yeniye sıralı. Sonuncu seri "canlı" olandır.
# --------------------------------------------------------------------------- #
CPI_CHAIN: list[dict] = [
    {
        "series": "TP.FG.U63",
        "label": "İTO İstanbul Ücretliler Geçinme Endeksi (1963=100)",
        "source": "İTO",
        "official": False,
    },
    {
        "series": "TP.FG.F01",
        "label": "TÜİK Tüketici Fiyat Endeksi (1978-79=100, arşiv)",
        "source": "TÜİK",
        "official": True,
    },
    {
        "series": "TP.GENENDEKS.T1",
        "label": "TÜİK Tüketici Fiyat Endeksi (2003=100)",
        "source": "TÜİK",
        "official": True,
    },
]

# TL'nin karşılaştırılacağı varlıklar (fiyatlar TL cinsinden, aylık ortalama).
#   kind="currency" -> birim para   "weight" -> gram   "count" -> adet/birim/varil
#   cpi_region      -> para biriminin "kendi" enflasyonu (app/foreign_cpi.py)
#   usd_series      -> varlığın dolar cinsinden fiyatı (varsa): "kendi" değer artışı
#   priced_in_usd   -> seri dolar cinsindendir; TL fiyatı USD/TL ile çarpılarak bulunur
ASSETS: dict[str, dict] = {
    "usd": {
        "series": "TP.DK.USD.A.YTL", "label": "Dolar", "symbol": "$",
        "kind": "currency", "cpi_region": "us",
    },
    "eur": {
        "series": "TP.DK.EUR.A.YTL", "label": "Euro", "symbol": "€",
        "kind": "currency", "cpi_region": "ea",
    },
    "gold": {
        "series": "TP.MK.KUL.YTL", "label": "Altın", "symbol": "gr",
        "kind": "weight", "usd_series": "TP.MK.LON.YTL", "usd_unit": "ons",
    },
    "cgold": {
        "series": "TP.MK.CUM.YTL", "label": "Cumhuriyet altını", "symbol": "adet",
        "kind": "count",
    },
    "bist": {
        "series": "TP.MK.F.BILESIK", "label": "BIST 100", "symbol": "birim",
        "kind": "count",
    },
    "brent": {
        "series": "TP.BRENTPETROL.EUBP", "label": "Brent petrol", "symbol": "varil",
        "kind": "count", "priced_in_usd": True,
    },
}

# Karşılaştırma/gösterge endeksleri. "ito" ayrıca hesaplama sonucunda ayrı satır olarak sunulur.
INDICES: dict[str, dict] = {
    "ito": {
        "series": "TP.FG.U63",
        "label": "İTO Ücretliler Geçinme Endeksi",
        "short": "İTO · İstanbul",
        "hint": "İstanbul Ticaret Odası — İstanbul geçinme endeksi",
        "source": "İTO",
    },
    "ufe": {
        "series": "TP.TUFE1YI.T1",
        "label": "Yurt İçi ÜFE",
        "short": "Yİ-ÜFE",
        "hint": "TÜİK — üretici fiyatları",
        "source": "TÜİK",
    },
    "konut": {
        "series": "TP.KFE.TR",
        "label": "Konut Fiyat Endeksi",
        "short": "Konut",
        "hint": "TCMB — Türkiye geneli konut fiyatları",
        "source": "TCMB",
    },
    "itotefe": {
        "series": "TP.FG.C01",
        "label": "İTO Toptan Eşya Fiyat Endeksi",
        "short": "Toptan eşya",
        "hint": "İstanbul Ticaret Odası — İstanbul toptan eşya",
        "source": "İTO",
    },
}


class EVDSError(Exception):
    """EVDS ile ilgili hatalar için özel istisna."""


# --------------------------------------------------------------------------- #
# Yanıt çözümleme
# --------------------------------------------------------------------------- #

def _value_key(series_code: str) -> str:
    """Seri kodundaki noktalar EVDS yanıtında alt çizgiye dönüşür (TP.FG.J0 -> TP_FG_J0)."""
    return series_code.replace(".", "_")


def _extract_value(item: dict, value_key: str) -> Optional[str]:
    """Bir satırdan değeri çıkarır. Bilinen alan adını dener,
    bulamazsa tarih/zaman dışındaki ilk sayısal alanı arar (esneklik için)."""
    if value_key in item and item[value_key] not in (None, "", "null"):
        return item[value_key]

    meta_fields = {"Tarih", "UNIXTIME", "YEARWEEK", "ARALIK"}
    for key, val in item.items():
        if key in meta_fields or val in (None, "", "null"):
            continue
        return val
    return None


def _parse_response(data: dict, series_code: str) -> dict[str, float]:
    """EVDS JSON yanıtını {"YYYY-MM": değer} sözlüğüne çevirir."""
    value_key = _value_key(series_code)
    items = data.get("items") or []
    result: dict[str, float] = {}

    for item in items:
        tarih = item.get("Tarih")  # "2003-1" formatında
        raw_value = _extract_value(item, value_key)
        if not tarih or raw_value is None:
            continue
        try:
            year, month = tarih.split("-")
            key = f"{int(year):04d}-{int(month):02d}"
            value = float(str(raw_value).replace(",", "."))
        except (ValueError, TypeError):
            continue
        # Sıfır/negatif endeks ya da fiyat anlamsızdır; bölme hatası yaratmasın.
        if value > 0:
            result[key] = value

    return result


async def _fetch_series(
    client: httpx.AsyncClient,
    api_key: str,
    series_code: str,
    aggregation: Optional[str] = None,
) -> dict[str, float]:
    """Tek bir EVDS serisini aylık olarak çeker ve {YYYY-MM: değer} döner."""
    today = datetime.date.today()
    # Yeni EVDS servisi parametreleri URL yoluna gömülmüş halde bekler.
    path = (
        f"series={series_code}"
        f"&startDate={_HISTORY_START}"
        f"&endDate={today.strftime('%d-%m-%Y')}"
        f"&type=json"
        f"&frequency={_MONTHLY_FREQUENCY}"
    )
    if aggregation:
        path += f"&aggregationTypes={aggregation}"

    try:
        resp = await client.get(f"{EVDS_BASE_URL}/{path}", headers={"key": api_key})
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise EVDSError(
            f"EVDS isteği başarısız (HTTP {exc.response.status_code}) — seri: {series_code}. "
            "API anahtarınızın doğru olduğundan emin olun."
        ) from exc
    except httpx.HTTPError as exc:
        raise EVDSError(f"EVDS'ye bağlanılamadı: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EVDSError(
            "EVDS beklenmeyen bir yanıt döndürdü (JSON çözümlenemedi). "
            "API anahtarı geçersiz olabilir."
        ) from exc

    parsed = _parse_response(data, series_code)
    if not parsed:
        raise EVDSError(f"EVDS'den '{series_code}' için değer çözümlenemedi.")
    return parsed


# --------------------------------------------------------------------------- #
# Zincirleme (chain-linking)
# --------------------------------------------------------------------------- #

def chain_indices(segments: list[tuple[dict, dict[str, float]]]) -> tuple[dict[str, float], list[dict]]:
    """Eskiden yeniye sıralı endeks parçalarını tek bir kesintisiz endekse birleştirir.

    En yeni seri temel alınır; her eski seri, iki serinin çakıştığı **en erken** ayda
    oran alınarak ölçeklenir ve endeksin başına eklenir. Böylece sonuçtaki endeksin
    seviyesi güncel TÜFE (2003=100) ile aynı kalır.

    Dönüş: (endeks, parça listesi). Parça listesi hangi ayın hangi kaynaktan geldiğini
    anlatır (arayüzdeki "1982 öncesi tahmini" uyarısı için).
    """
    usable = [(meta, values) for meta, values in segments if values]
    if not usable:
        return {}, []

    meta_newest, values_newest = usable[-1]
    index: dict[str, float] = dict(values_newest)
    provenance: list[dict] = [{
        **{k: meta_newest[k] for k in ("series", "label", "source", "official")},
        "start": min(index),
        "end": max(index),
    }]

    for meta, values in reversed(usable[:-1]):
        link = min(index)  # zincirin şu anki en eski ayı
        if link not in values:
            continue  # çakışma yok → bu parça eklenemez
        ratio = index[link] / values[link]
        older = {m: v * ratio for m, v in values.items() if m < link}
        if not older:
            continue
        index.update(older)
        provenance.insert(0, {
            **{k: meta[k] for k in ("series", "label", "source", "official")},
            "start": min(older),
            "end": max(older),
        })

    return index, provenance


# --------------------------------------------------------------------------- #
# Toplu çekme
# --------------------------------------------------------------------------- #

async def _fetch_all(api_key: str) -> dict:
    """TÜFE zincirini, varlık fiyatlarını ve gösterge endekslerini birlikte çeker."""
    if not api_key or api_key.startswith("BURAYA"):
        raise EVDSError(
            "EVDS API anahtarı tanımlı değil. Lütfen .env dosyasındaki "
            "EVDS_API_KEY değerini doldurun."
        )

    # (isim, seri kodu, aggregation, zorunlu mu?)
    jobs: list[tuple[str, str, Optional[str], bool]] = []
    for i, seg in enumerate(CPI_CHAIN):
        # Yalnızca canlı (son) seri zorunludur; arşiv parçaları çekilemezse tarih aralığı kısalır.
        jobs.append((f"cpi:{i}", seg["series"], None, i == len(CPI_CHAIN) - 1))
    for key, meta in ASSETS.items():
        jobs.append((f"asset:{key}", meta["series"], "avg", False))
        if meta.get("usd_series"):
            jobs.append((f"assetusd:{key}", meta["usd_series"], "avg", False))
    for key, meta in INDICES.items():
        jobs.append((f"index:{key}", meta["series"], None, False))

    # Aynı seri birden çok yerde kullanılabilir (ör. İTO hem zincirde hem gösterge);
    # her seriyi bir kez çekip sonucu paylaşırız.
    unique: dict[tuple[str, Optional[str]], list[str]] = {}
    for name, series, agg, _ in jobs:
        unique.setdefault((series, agg), []).append(name)

    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
        async def run(series: str, agg: Optional[str]):
            async with semaphore:
                return await _fetch_series(client, api_key, series, agg)

        keys = list(unique)
        results = await asyncio.gather(*(run(s, a) for s, a in keys), return_exceptions=True)

    fetched: dict[str, dict[str, float]] = {}
    errors: dict[str, str] = {}
    for (series, agg), outcome in zip(keys, results):
        for name in unique[(series, agg)]:
            if isinstance(outcome, Exception):
                errors[name] = str(outcome)
            else:
                fetched[name] = outcome

    # Zorunlu seriler gelmediyse tümüyle başarısız say (önbelleğe düşülür).
    for name, series, _agg, required in jobs:
        if required and name not in fetched:
            raise EVDSError(errors.get(name, f"Zorunlu seri çekilemedi: {series}"))

    tufe, segments = chain_indices(
        [(seg, fetched.get(f"cpi:{i}", {})) for i, seg in enumerate(CPI_CHAIN)]
    )

    usd = fetched.get("asset:usd", {})
    assets: dict[str, dict[str, float]] = {}
    assets_usd: dict[str, dict[str, float]] = {}
    for key, meta in ASSETS.items():
        prices = fetched.get(f"asset:{key}")
        if not prices:
            continue
        if meta.get("priced_in_usd"):
            # Dolar cinsinden kotalanan varlık (Brent): TL fiyatı = USD fiyatı × USD/TL
            assets_usd[key] = prices
            prices = {m: v * usd[m] for m, v in prices.items() if m in usd}
            if not prices:
                continue
        assets[key] = prices
        if fetched.get(f"assetusd:{key}"):
            assets_usd[key] = fetched[f"assetusd:{key}"]

    indices = {key: fetched[f"index:{key}"] for key in INDICES if fetched.get(f"index:{key}")}

    if errors:
        print(f"[UYARI] Bazı EVDS serileri çekilemedi: {', '.join(sorted(errors))}")

    return {
        "tufe": tufe,
        "segments": segments,
        "assets": assets,
        "assets_usd": assets_usd,
        "indices": indices,
    }


# --------------------------------------------------------------------------- #
# Önbellek
# --------------------------------------------------------------------------- #

def _read_cache() -> Optional[dict]:
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(series: dict) -> dict:
    payload = {"fetched_at": time.time(), "schema": CACHE_SCHEMA, **series}
    # Diske yazmayı dene. Salt-okunur dosya sistemlerinde (ör. Vercel gibi serverless
    # ortamlar) yazma başarısız olabilir; bu durumda taze veriyi yalnızca bellekte
    # tutup devam ederiz — uygulama çökmemeli.
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    except OSError as exc:
        print(f"[UYARI] Önbellek diske yazılamadı (salt-okunur olabilir): {exc}")
    return payload


class DataService:
    """EVDS verisini yöneten servis: önbellek + çekme mantığı."""

    def __init__(self, api_key: str, cache_ttl: int):
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self._payload: Optional[dict] = None
        self._lock = asyncio.Lock()

    def _has_api_key(self) -> bool:
        """Kullanılabilir bir EVDS anahtarı var mı? (boş/yer-tutucu değilse)"""
        return bool(self.api_key) and not self.api_key.startswith("BURAYA")

    def _is_fresh(self, payload: dict) -> bool:
        return (time.time() - payload.get("fetched_at", 0)) < self.cache_ttl

    @staticmethod
    def _cache_matches(payload: dict) -> bool:
        return payload.get("schema") == CACHE_SCHEMA and bool(payload.get("tufe"))

    async def ensure_loaded(self, force: bool = False) -> dict:
        """Veriyi belleğe yükler. Sırasıyla: bellek -> disk önbellek -> EVDS."""
        async with self._lock:
            if not force and self._payload and self._is_fresh(self._payload):
                return self._payload

            if not force:
                cached = _read_cache()
                if cached and self._cache_matches(cached) and self._is_fresh(cached):
                    self._payload = cached
                    return self._payload

            # API anahtarı yoksa (veya yer-tutucuysa) EVDS'e hiç gidilmez; depoya gömülü
            # önbellek bel kemiği olur. Böylece anahtarsız klonlamada bile uygulama çalışır.
            if not self._has_api_key():
                fallback = self._payload or _read_cache()
                if fallback and self._cache_matches(fallback):
                    self._payload = fallback
                    return self._payload
                raise EVDSError(
                    "EVDS API anahtarı tanımlı değil ve kullanılabilir bir önbellek yok. "
                    "Lütfen .env içindeki EVDS_API_KEY değerini doldurun ya da "
                    "cache/data_cache.json dosyasının mevcut olduğundan emin olun."
                )

            try:
                series = await asyncio.wait_for(
                    _fetch_all(self.api_key), timeout=FETCH_BUDGET_SECONDS)
                self._payload = _write_cache(series)
                return self._payload
            except (EVDSError, asyncio.TimeoutError) as exc:
                # Çekme başarısız olur ya da süre bütçesini aşarsa eldeki (bayat olsa da)
                # veriye düş — sunucusuz ortamda soğuk başlangıcın zaman aşımına uğramaması için.
                fallback = self._payload or _read_cache()
                if fallback and self._cache_matches(fallback):
                    if isinstance(exc, asyncio.TimeoutError):
                        print(f"[UYARI] EVDS {FETCH_BUDGET_SECONDS}sn içinde yanıt vermedi; "
                              "önbellekle devam ediliyor.")
                    self._payload = fallback
                    return self._payload
                if isinstance(exc, asyncio.TimeoutError):
                    raise EVDSError(
                        f"EVDS {FETCH_BUDGET_SECONDS} saniye içinde yanıt vermedi ve "
                        "kullanılabilir bir önbellek yok."
                    ) from exc
                raise

    # ------------------------------------------------------------------ #
    # Okuyucular
    # ------------------------------------------------------------------ #

    def get_tufe(self) -> dict[str, float]:
        return (self._payload or {}).get("tufe", {})

    def get_segments(self) -> list[dict]:
        """TÜFE zincirinin hangi ayının hangi seriden geldiğini anlatan liste."""
        return (self._payload or {}).get("segments", [])

    def get_assets(self) -> dict[str, dict]:
        """{'usd': {YYYY-MM: fiyat}, 'gold': {...}, ...} — TL cinsinden."""
        return (self._payload or {}).get("assets", {})

    def get_assets_usd(self) -> dict[str, dict]:
        """Varlığın dolar cinsinden fiyatı (altın için ons, Brent için varil)."""
        return (self._payload or {}).get("assets_usd", {})

    def get_indices(self) -> dict[str, dict]:
        """{'ito': {YYYY-MM: endeks}, 'ufe': {...}, ...}"""
        return (self._payload or {}).get("indices", {})

    def get_index(self, key: str) -> dict[str, float]:
        return self.get_indices().get(key, {})

    def official_start(self) -> Optional[str]:
        """Resmi (TÜİK) verinin başladığı ay. Öncesi tahminidir."""
        official = [s["start"] for s in self.get_segments() if s.get("official")]
        return min(official) if official else None

    def get_meta(self) -> dict:
        tufe = self.get_tufe()
        keys = sorted(tufe.keys())
        assets = self.get_assets()
        indices = self.get_indices()
        return {
            "base": "2003=100",
            "source": "TCMB EVDS",
            "fetched_at": (self._payload or {}).get("fetched_at"),
            "start": keys[0] if keys else None,
            "end": keys[-1] if keys else None,
            "count": len(keys),
            "official_start": self.official_start(),
            "segments": self.get_segments(),
            "assets": {
                k: {
                    "label": m["label"], "symbol": m["symbol"], "kind": m["kind"],
                    "start": min(assets[k]), "end": max(assets[k]),
                }
                for k, m in ASSETS.items() if assets.get(k)
            },
            "indices": {
                k: {
                    "label": m["label"], "hint": m["hint"], "source": m["source"],
                    "start": min(indices[k]), "end": max(indices[k]),
                }
                for k, m in INDICES.items() if indices.get(k)
            },
        }
