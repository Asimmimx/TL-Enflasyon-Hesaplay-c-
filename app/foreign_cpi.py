"""
Yabancı para birimlerinin **kendi** enflasyonu — ABD (dolar) ve Euro Bölgesi (euro).

Dolar/TL kurunun artması TL'nin değer kaybını gösterir; ama doların kendisi de ABD'de
enflasyona uğrar. Bu modül, o "kendi içindeki" enflasyonu hesaplamak için resmi **yıllık
ortalama** TÜFE oranlarını tutar. Kaynaklar:
  - ABD: BLS — CPI-U (All items, U.S. city average), yıllık ortalama değişim (%).
  - Euro Bölgesi: Eurostat — HICP (All-items, Euro area / EA), yıllık ortalama değişim (%).

Not: Veri **yıl bazlıdır** (aylık değil) — arayüzde "yaklaşık" olarak etiketlenir. ENAG/asgari
ücret tabloları gibi elle tutulur; yeni yıl açıklandığında ilgili sözlüğe eklenir. Canlı API yok,
çevrimdışı çalışır.

2024 ve öncesi tarihsel kesin yıllık ortalamalardır; **2025** kesinleşmiş yıllık ortalamadır.
**2026 geçicidir** — yıl tamamlanmadığı için o yıl yayımlanan **en güncel 12 aylık** enflasyondur
(ABD: Nisan 2026 = %3,8; Euro Bölgesi: Mayıs 2026 = %3,2). Son güncelleme: Haziran 2026.
"""

from __future__ import annotations

_BASE_YEAR = 2003  # endeks tabanı (= 100)

# Yıl -> yıllık ortalama TÜFE değişimi (%). _BASE_YEAR'ın kendi oranı kullanılmaz (taban).
_RATES: dict[str, dict[int, float]] = {
    "us": {  # BLS, CPI-U, yıllık ortalama
        2004: 2.7, 2005: 3.4, 2006: 3.2, 2007: 2.9, 2008: 3.8, 2009: -0.4,
        2010: 1.6, 2011: 3.2, 2012: 2.1, 2013: 1.5, 2014: 1.6, 2015: 0.1,
        2016: 1.3, 2017: 2.1, 2018: 2.4, 2019: 1.8, 2020: 1.2, 2021: 4.7,
        2022: 8.0, 2023: 4.1, 2024: 2.9, 2025: 2.6, 2026: 3.8,  # 2026 geçici: Nisan 2026 (12 aylık)
    },
    "ea": {  # Eurostat, HICP, Euro Bölgesi, yıllık ortalama
        2004: 2.2, 2005: 2.2, 2006: 2.2, 2007: 2.1, 2008: 3.3, 2009: 0.3,
        2010: 1.6, 2011: 2.7, 2012: 2.5, 2013: 1.4, 2014: 0.4, 2015: 0.2,
        2016: 0.2, 2017: 1.5, 2018: 1.8, 2019: 1.2, 2020: 0.3, 2021: 2.6,
        2022: 8.4, 2023: 5.4, 2024: 2.4, 2025: 2.2, 2026: 3.2,  # 2026 geçici: Mayıs 2026 (12 aylık)
    },
}

_LABELS: dict[str, str] = {"us": "ABD", "ea": "Euro Bölgesi"}


def _build_index(region: str) -> dict[int, float]:
    """Yıllık oranlardan kümülatif fiyat endeksi kurar (_BASE_YEAR = 100)."""
    rates = _RATES.get(region, {})
    index = {_BASE_YEAR: 100.0}
    for year in sorted(rates):
        index[year] = index[year - 1] * (1 + rates[year] / 100.0)
    return index


_INDEX: dict[str, dict[int, float]] = {region: _build_index(region) for region in _RATES}


def label(region: str) -> str | None:
    """Bölgenin Türkçe adı ('ABD' / 'Euro Bölgesi')."""
    return _LABELS.get(region)


def period_change(region: str, start_year: int, end_year: int) -> float | None:
    """start_year → end_year arası kümülatif (yıllık bazlı) enflasyon (%).

    end_year veride yoksa (ör. henüz tamamlanmamış yıl) en güncel tam yıla çekilir.
    Dönem dejenere olursa (≤ 0 yıl) None döner — yanıltıcı %0 göstermemek için.
    """
    index = _INDEX.get(region)
    if not index:
        return None
    last = max(index)
    end = min(end_year, last)
    if start_year not in index or end not in index or end <= start_year:
        return None
    return (index[end] / index[start_year] - 1) * 100
