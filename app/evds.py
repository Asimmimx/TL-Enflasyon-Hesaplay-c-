"""
TCMB EVDS (Elektronik Veri Dağıtım Sistemi) istemcisi.

Aylık TÜFE (Tüketici Fiyat Endeksi) ve USD/TL kuru verilerini EVDS'den çeker,
diske önbellekler (cache) ve uygulamaya sade sözlükler olarak sunar.

EVDS hakkında:
  - TÜFE Genel Endeksi serisi:  TP.FG.J0        (2003 = 100 bazlı)
  - USD/TL (döviz alış):        TP.DK.USD.A.YTL (TL cinsinden, aylık ortalama)
  - Yeni servis adresi (2024+): https://evds3.tcmb.gov.tr/igmevdsms-dis
  - İstek biçimi: parametreler URL yoluna (path) gömülür; API anahtarı 'key'
    HTTP başlığı (header) ile gönderilir.
  - Örnek: .../igmevdsms-dis/series=TP.FG.J0&startDate=01-01-2003&endDate=...&type=json&frequency=5
"""

from __future__ import annotations

import json
import time
import asyncio
import datetime
from pathlib import Path
from typing import Optional

import httpx

EVDS_BASE_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
CACHE_FILE = Path(__file__).resolve().parent.parent / "cache" / "data_cache.json"

# TL'nin karşılaştırılacağı varlıklar (hepsi TL cinsinden, aylık ortalama).
#   kind="currency" -> birim para (dolar/euro), "weight" -> gram (altın)
ASSETS: dict[str, dict] = {
    "usd":  {"series": "TP.DK.USD.A.YTL", "label": "Dolar", "symbol": "$",  "kind": "currency"},
    "eur":  {"series": "TP.DK.EUR.A.YTL", "label": "Euro",  "symbol": "€",  "kind": "currency"},
    "gold": {"series": "TP.MK.KUL.YTL",   "label": "Altın", "symbol": "gr", "kind": "weight"},
}

# EVDS frekans kodu: 5 = Aylık
_MONTHLY_FREQUENCY = 5


class EVDSError(Exception):
    """EVDS ile ilgili hatalar için özel istisna."""


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
            result[key] = float(str(raw_value).replace(",", "."))
        except (ValueError, TypeError):
            continue

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
        f"&startDate=01-01-2003"
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
        raise EVDSError(f"EVDS'den '{series_code}' için endeks değeri çözümlenemedi.")
    return parsed


async def _fetch_all(api_key: str, tufe_series: str) -> dict:
    """TÜFE ve USD/TL serilerini birlikte çeker."""
    if not api_key or api_key.startswith("BURAYA"):
        raise EVDSError(
            "EVDS API anahtarı tanımlı değil. Lütfen .env dosyasındaki "
            "EVDS_API_KEY değerini doldurun."
        )

    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
        tasks = [_fetch_series(client, api_key, tufe_series)]
        tasks += [
            _fetch_series(client, api_key, meta["series"], aggregation="avg")
            for meta in ASSETS.values()
        ]
        results = await asyncio.gather(*tasks)
    tufe = results[0]
    assets = {key: results[i + 1] for i, key in enumerate(ASSETS)}
    return {"tufe": tufe, "assets": assets}


def _read_cache() -> Optional[dict]:
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(tufe_series: str, series: dict) -> dict:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": time.time(),
        "tufe_series": tufe_series,
        "asset_keys": sorted(ASSETS),
        "tufe": series["tufe"],
        "assets": series["assets"],
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


class DataService:
    """TÜFE ve USD/TL verisini yöneten servis: önbellek + EVDS çekme mantığı."""

    def __init__(self, api_key: str, tufe_series: str, cache_ttl: int):
        self.api_key = api_key
        self.tufe_series = tufe_series
        self.cache_ttl = cache_ttl
        self._payload: Optional[dict] = None
        self._lock = asyncio.Lock()

    def _has_api_key(self) -> bool:
        """Kullanılabilir bir EVDS anahtarı var mı? (boş/yer-tutucu değilse)"""
        return bool(self.api_key) and not self.api_key.startswith("BURAYA")

    def _is_fresh(self, payload: dict) -> bool:
        return (time.time() - payload.get("fetched_at", 0)) < self.cache_ttl

    def _cache_matches(self, payload: dict) -> bool:
        return (
            payload.get("tufe_series") == self.tufe_series
            and "tufe" in payload
            and payload.get("asset_keys") == sorted(ASSETS)
        )

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
                series = await _fetch_all(self.api_key, self.tufe_series)
                self._payload = _write_cache(self.tufe_series, series)
                return self._payload
            except EVDSError:
                # Çekme başarısız olursa eldeki (bayat olsa da) veriye düş
                fallback = self._payload or _read_cache()
                if fallback and self._cache_matches(fallback):
                    self._payload = fallback
                    return self._payload
                raise

    def get_tufe(self) -> dict[str, float]:
        return (self._payload or {}).get("tufe", {})

    def get_assets(self) -> dict[str, dict]:
        """{'usd': {YYYY-MM: fiyat}, 'eur': {...}, 'gold': {...}}"""
        return (self._payload or {}).get("assets", {})

    def get_meta(self) -> dict:
        tufe = self.get_tufe()
        keys = sorted(tufe.keys())
        return {
            "tufe_series": self.tufe_series,
            "assets": {k: m["label"] for k, m in ASSETS.items()},
            "base": "2003=100",
            "source": "TCMB EVDS",
            "fetched_at": (self._payload or {}).get("fetched_at"),
            "start": keys[0] if keys else None,
            "end": keys[-1] if keys else None,
            "count": len(keys),
        }
