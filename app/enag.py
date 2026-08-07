"""
ENAG (Enflasyon Araştırma Grubu) — bağımsız "reel enflasyon" verisi.

ÖNEMLİ — VERİ KAYNAĞI VE GÜVENİLİRLİK NOTU
-------------------------------------------
ENAG'ın herkese açık bir API'si YOKTUR ve resmi sitesi (enagrup.org) otomatik
erişime kapalıdır (Cloudflare HTTP 525). Bu yüzden ENAG verisi EVDS gibi canlı
çekilemez; aşağıdaki aylık oranlar basında duyurulan açıklamalardan derlenmiştir.

Bu ham aylık veriyi, ENAG'ın geniş kabul gören **yıllık** oranlarına göre yıl bazında
NORMALİZE ediyoruz; böylece her yılın bileşik enflasyonu resmi yıllık rakamla birebir
tutar. Yıllık çapası olmayan dönemler (içinde bulunulan yıl) ham haliyle kullanılır ve
"doğrulanmamış" olarak işaretlenir.

Bazı aylar için ENAG'ın açıkladığı aylık oran basında bulunamadı; bu aylar ENAG'ın
o ay için duyurduğu **12 aylık** orandan geriye doğru türetilmiştir
(m_t = (1+A_t)/(1+A_{t-1}) × (1+m_{t-12}) − 1). Türetilen değerler ± ~0,3 puan
hassasiyetindedir ve yıl normalizasyonu bu sapmayı yıl sonunda sıfırlar.

Veriyi güncellemek için: ENAG yeni ayı açıkladığında ENAG_MONTHLY_RATES'e ekleyin
(örn. "2026-07": 2.4) ve yıl kapanınca ENAG_ANNUAL_OFFICIAL çapasını girin.

Son güncelleme: 7 Ağustos 2026 (ENAG Temmuz 2026 verisine kadar).
"""

from __future__ import annotations

import math

# Aylık ENAG enflasyon oranları (%) — ham veri.
ENAG_MONTHLY_RATES: dict[str, float] = {
    # 2020: ENAG Eylül 2020'de kuruldu; gerçek zamanlı aylık veri o tarihte başlar.
    # Yıl sonu (2020) ENAG enflasyonu resmi olarak %36,72'dir ve Aralık 2020 aylık oranı
    # %4,08'dir. Ocak–Kasım 2020, doğrulanmış yıllık orana eşit dağıtılmış yaklaşık
    # değerlerdir (yıl bazında normalizasyon ile tam %36,72 tutar).
    "2020-01": 2.51, "2020-02": 2.51, "2020-03": 2.51, "2020-04": 2.51,
    "2020-05": 2.51, "2020-06": 2.51, "2020-07": 2.51, "2020-08": 2.51,
    "2020-09": 2.51, "2020-10": 2.51, "2020-11": 2.51, "2020-12": 4.08,
    "2021-01": 3.28, "2021-02": 2.85, "2021-03": 4.02, "2021-04": 4.15,
    "2021-05": 4.10, "2021-06": 3.98, "2021-07": 4.50, "2021-08": 3.85,
    "2021-09": 4.95, "2021-10": 6.20, "2021-11": 9.60, "2021-12": 19.15,
    "2022-01": 15.80, "2022-02": 8.35, "2022-03": 9.45, "2022-04": 11.20,
    "2022-05": 6.30, "2022-06": 8.95, "2022-07": 5.20, "2022-08": 4.05,
    "2022-09": 6.15, "2022-10": 7.25, "2022-11": 5.95, "2022-12": 3.20,
    "2023-01": 9.35, "2023-02": 5.80, "2023-03": 5.05, "2023-04": 5.40,
    "2023-05": 1.85, "2023-06": 7.50, "2023-07": 14.20, "2023-08": 13.45,
    "2023-09": 7.65, "2023-10": 5.80, "2023-11": 5.35, "2023-12": 4.85,
    # 2024 — Ağustos/Kasım/Aralık ENAG duyurularından; Eylül/Ekim yıllık orandan türetildi.
    "2024-01": 9.85, "2024-02": 6.70, "2024-03": 4.65, "2024-04": 4.70,
    "2024-05": 3.37, "2024-06": 2.40, "2024-07": 4.75, "2024-08": 3.47,
    "2024-09": 5.23, "2024-10": 5.83, "2024-11": 4.06, "2024-12": 2.34,
    # 2025 — Nisan, Haziran–Aralık ENAG duyurularından; Ocak–Mart ve Mayıs türetildi.
    "2025-01": 8.22, "2025-02": 3.52, "2025-03": 3.78, "2025-04": 4.46,
    "2025-05": 3.66, "2025-06": 3.05, "2025-07": 3.75, "2025-08": 3.23,
    "2025-09": 3.79, "2025-10": 3.74, "2025-11": 2.13, "2025-12": 2.11,
    # 2026 — ENAG duyuruları (yıl kapanmadığı için çapasız → "doğrulanmamış").
    "2026-01": 6.32, "2026-02": 4.01, "2026-03": 4.10, "2026-04": 5.07,
    "2026-05": 2.16, "2026-06": 1.94, "2026-07": 3.07,
}

# ENAG'ın geniş kabul gören yıl sonu (12 aylık) enflasyon oranları (%).
# Aylık veri bu çapalara göre normalize edilir.
ENAG_ANNUAL_OFFICIAL: dict[int, float] = {
    2020: 36.72,
    2021: 82.81,
    2022: 137.55,
    2023: 127.21,
    2024: 83.40,
    2025: 56.14,
}


def _build_index() -> tuple[dict[str, float], set[int]]:
    """Aylık oranlardan kümülatif ENAG endeksi üretir.

    Yıllık resmi çapası olan yıllar için o yılın aylık çarpanları, bileşikleri resmi
    yıllık orana eşit olacak şekilde log-uzayında ölçeklenir.
    İç temel: 2019-12 = 100 (kullanıcıya sunulan ilk ay 2020-01).
    """
    months = sorted(ENAG_MONTHLY_RATES)

    by_year: dict[int, list[str]] = {}
    for m in months:
        by_year.setdefault(int(m[:4]), []).append(m)

    adjusted_factor: dict[str, float] = {}
    verified_years: set[int] = set()

    for year, year_months in by_year.items():
        raw_factors = [1 + ENAG_MONTHLY_RATES[m] / 100 for m in year_months]
        anchor = ENAG_ANNUAL_OFFICIAL.get(year)
        if anchor is not None and len(year_months) == 12:
            raw_total = math.prod(raw_factors)
            target = 1 + anchor / 100
            # Her çarpanı p kuvvetine al: çarpımları tam olarak hedefe eşitlenir.
            power = math.log(target) / math.log(raw_total)
            for m in year_months:
                adjusted_factor[m] = (1 + ENAG_MONTHLY_RATES[m] / 100) ** power
            verified_years.add(year)
        else:
            for m in year_months:
                adjusted_factor[m] = 1 + ENAG_MONTHLY_RATES[m] / 100

    level = 100.0  # ilk ayın bir önceki ayı = 100 (iç temel)
    # Taban ay da endekse konur; böylece ilk yılın Aralık→Aralık değişimi hesaplanabilir.
    index: dict[str, float] = {}
    if months:
        index[_prev_month(months[0])] = level
    for m in months:
        level *= adjusted_factor[m]
        index[m] = round(level, 6)
    return index, verified_years


def _prev_month(month_key: str) -> str:
    year, month = (int(x) for x in month_key.split("-"))
    return f"{year - 1:04d}-12" if month == 1 else f"{year:04d}-{month - 1:02d}"


ENAG_INDEX, _VERIFIED_YEARS = _build_index()


def coverage() -> dict:
    """ENAG'ın gerçek veri kapsamı (taban ay hariç)."""
    keys = sorted(ENAG_MONTHLY_RATES)
    return {
        "start": keys[0] if keys else None,
        "end": keys[-1] if keys else None,
        "verified_years": sorted(_VERIFIED_YEARS),
    }


def index() -> dict[str, float]:
    """Tüm ENAG endeksi ({'YYYY-MM': değer})."""
    return ENAG_INDEX


def get_index(month_key: str):
    """'YYYY-MM' için ENAG endeks değerini döner (yoksa None)."""
    return ENAG_INDEX.get(month_key)


def is_verified(month_key: str) -> bool:
    """Bu ay, resmi yıllık orana çapalanmış (doğrulanmış) bir yıla mı ait?"""
    try:
        return int(month_key[:4]) in _VERIFIED_YEARS
    except (ValueError, TypeError):
        return False
