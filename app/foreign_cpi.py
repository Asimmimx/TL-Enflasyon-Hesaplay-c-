"""
Yabancı para birimlerinin **kendi** enflasyonu — ABD (dolar) ve Euro Bölgesi (euro).

Dolar/TL kurunun artması TL'nin değer kaybını gösterir; ama doların kendisi de ABD'de
enflasyona uğrar. Bu modül, o "kendi içindeki" enflasyonu hesaplamak için resmi **yıllık
ortalama** TÜFE oranlarını tutar. Kaynaklar:
  - ABD: BLS — CPI-U (All items, U.S. city average), yıllık ortalama değişim (%), 1950'den.
  - Euro Bölgesi: Eurostat — HICP (All-items, Euro area), yıllık ortalama değişim (%), 1997'den.
    (Euro 1999'da doğdu; EUR/TL serisi de 1999'da başlar.)

Not: Veri **yıl bazlıdır** (aylık değil) — arayüzde "yaklaşık" olarak etiketlenir. ENAG/asgari
ücret tabloları gibi elle tutulur; yeni yıl açıklandığında ilgili sözlüğe eklenir. Canlı API yok,
çevrimdışı çalışır.

2025 ve öncesi kesinleşmiş yıllık ortalamalardır. **2026 geçicidir** — yıl tamamlanmadığı için
o yıl yayımlanan **en güncel 12 aylık** enflasyondur (ABD: Haziran 2026 = %3,5;
Euro Bölgesi: Haziran 2026 = %2,8). Son güncelleme: Ağustos 2026.
"""

from __future__ import annotations

# Bölge -> (endeks tabanı yılı, yıl -> yıllık ortalama TÜFE değişimi %).
# Taban yılın kendi oranı kullanılmaz; endeks o yılda 100 kabul edilir.
_BASE_YEAR: dict[str, int] = {"us": 1949, "ea": 1996}

_RATES: dict[str, dict[int, float]] = {
    "us": {  # BLS, CPI-U, yıllık ortalama
        1950: 1.3, 1951: 7.9, 1952: 1.9, 1953: 0.8, 1954: 0.7, 1955: -0.4,
        1956: 1.5, 1957: 3.3, 1958: 2.8, 1959: 0.7, 1960: 1.7, 1961: 1.0,
        1962: 1.0, 1963: 1.3, 1964: 1.3, 1965: 1.6, 1966: 2.9, 1967: 3.1,
        1968: 4.2, 1969: 5.5, 1970: 5.7, 1971: 4.4, 1972: 3.2, 1973: 6.2,
        1974: 11.0, 1975: 9.1, 1976: 5.8, 1977: 6.5, 1978: 7.6, 1979: 11.3,
        1980: 13.5, 1981: 10.3, 1982: 6.2, 1983: 3.2, 1984: 4.3, 1985: 3.6,
        1986: 1.9, 1987: 3.6, 1988: 4.1, 1989: 4.8, 1990: 5.4, 1991: 4.2,
        1992: 3.0, 1993: 3.0, 1994: 2.6, 1995: 2.8, 1996: 3.0, 1997: 2.3,
        1998: 1.6, 1999: 2.2, 2000: 3.4, 2001: 2.8, 2002: 1.6, 2003: 2.3,
        2004: 2.7, 2005: 3.4, 2006: 3.2, 2007: 2.8, 2008: 3.8, 2009: -0.4,
        2010: 1.6, 2011: 3.2, 2012: 2.1, 2013: 1.5, 2014: 1.6, 2015: 0.1,
        2016: 1.3, 2017: 2.1, 2018: 2.4, 2019: 1.8, 2020: 1.2, 2021: 4.7,
        2022: 8.0, 2023: 4.1, 2024: 2.9, 2025: 2.6,
        2026: 3.5,  # geçici: Haziran 2026 (12 aylık)
    },
    "ea": {  # Eurostat, HICP, Euro Bölgesi, yıllık ortalama
        1997: 1.7, 1998: 1.1, 1999: 1.1, 2000: 2.1, 2001: 2.3, 2002: 2.3,
        2003: 2.1, 2004: 2.2, 2005: 2.2, 2006: 2.2, 2007: 2.1, 2008: 3.3,
        2009: 0.3, 2010: 1.6, 2011: 2.7, 2012: 2.5, 2013: 1.4, 2014: 0.4,
        2015: 0.2, 2016: 0.2, 2017: 1.5, 2018: 1.8, 2019: 1.2, 2020: 0.3,
        2021: 2.6, 2022: 8.4, 2023: 5.4, 2024: 2.4, 2025: 2.2,
        2026: 2.8,  # geçici: Haziran 2026 (12 aylık)
    },
}

_LABELS: dict[str, str] = {"us": "ABD", "ea": "Euro Bölgesi"}


def _build_index(region: str) -> dict[int, float]:
    """Yıllık oranlardan kümülatif fiyat endeksi kurar (taban yıl = 100)."""
    rates = _RATES.get(region, {})
    base = _BASE_YEAR[region]
    index = {base: 100.0}
    for year in sorted(rates):
        index[year] = index[year - 1] * (1 + rates[year] / 100.0)
    return index


_INDEX: dict[str, dict[int, float]] = {region: _build_index(region) for region in _RATES}


def label(region: str) -> str | None:
    """Bölgenin Türkçe adı ('ABD' / 'Euro Bölgesi')."""
    return _LABELS.get(region)


def coverage(region: str) -> dict | None:
    """Bölge verisinin kapsadığı yıl aralığı."""
    index = _INDEX.get(region)
    if not index:
        return None
    return {"start": min(index), "end": max(index), "label": _LABELS.get(region)}


def period_change(region: str, start_year: int, end_year: int) -> float | None:
    """start_year → end_year arası kümülatif (yıllık bazlı) enflasyon (%).

    Aralık verinin dışına taşarsa mevcut uçlara kırpılır (ör. henüz tamamlanmamış yıl
    ya da euro öncesi bir başlangıç). Dönem dejenere olursa (≤ 0 yıl) None döner —
    yanıltıcı %0 göstermemek için.
    """
    index = _INDEX.get(region)
    if not index:
        return None
    first, last = min(index), max(index)
    start = max(start_year, first)
    end = min(end_year, last)
    if start not in index or end not in index or end <= start:
        return None
    return (index[end] / index[start] - 1) * 100
