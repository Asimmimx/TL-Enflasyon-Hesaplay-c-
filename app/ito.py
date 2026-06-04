"""
İTO (İstanbul Ticaret Odası) — "İstanbul Ücretliler Geçinme Endeksi".

TÜİK dışında en sık atıf yapılan alternatif enflasyon ölçümü. Aylık veri 2003'ten
itibaren mevcuttur. İTO'nun açık bir API'si yoktur; aylık oranlar topluluk kaynaklı
olarak derlenmiştir (app/data/ito_data.json, kaynak: enflasyon-matrix).

DOĞRULUK YAKLAŞIMI — "spread" yöntemi
-------------------------------------
Topluluk verisinin ham mutlak değerleri eski yıllarda resmi TÜFE'den sapıyordu
(2005→2024 için ~%17). Ancak aynı derlemedeki TÜİK ve İTO serileri benzer sapmaya
sahip olduğundan, ikisinin ORANI (İTO/TÜİK farkı) güvenilirdir ve ortak sapma birbirini
götürür. Bu yüzden İTO sonucunu şöyle hesaplıyoruz:

    İTO_sonuç = resmi_TÜFE_sonuç × ( spread[bitiş] / spread[başlangıç] )
    spread[m] = İTO_endeks[m] / TÜİK_topluluk_endeks[m]

Böylece resmi TÜFE (EVDS) bel kemiği olarak kalır; topluluk verisinden yalnızca
İTO–TÜİK farkı alınır. Bu, eski yıllardaki sapmayı büyük ölçüde düzeltir.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parent / "data" / "ito_data.json"


def _build_index(rates: dict[str, float]) -> dict[str, float]:
    """Aylık oranlardan kümülatif endeks (iç temel = 100)."""
    index: dict[str, float] = {}
    level = 100.0
    for key in sorted(rates):
        level *= 1 + rates[key] / 100
        index[key] = level
    return index


def _load() -> dict[str, float]:
    try:
        raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    ito = raw.get("ito", {})
    tuik = raw.get("tuik_community", {})
    ito_idx = _build_index(ito)
    tuik_idx = _build_index(tuik)
    # spread = İTO / TÜİK (topluluk) — ortak sapma birbirini götürür
    spread: dict[str, float] = {}
    for key in ito_idx:
        if key in tuik_idx and tuik_idx[key]:
            spread[key] = ito_idx[key] / tuik_idx[key]
    return spread


SPREAD = _load()


def coverage() -> dict:
    keys = sorted(SPREAD)
    return {
        "start": keys[0] if keys else None,
        "end": keys[-1] if keys else None,
        "count": len(keys),
    }


def get_spread(month_key: str):
    """'YYYY-MM' için İTO/TÜİK fark katsayısını döner (yoksa None)."""
    return SPREAD.get(month_key)
