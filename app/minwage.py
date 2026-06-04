"""
Net aylık asgari ücret (TL) — yıllara göre.

Her yılın **Ocak** (yıl başı) net asgari ücreti kullanılır. 2003–2004 değerleri
2005 öncesi (eski TL) tutarların yeni TL karşılığıdır (1 YTL = 1.000.000 eski TL).

Kaynak: ocalhukuk.com / kamuya açık asgari ücret tabloları. Yeni yıl açıklandığında
aşağıdaki sözlüğe eklenebilir.
"""

from __future__ import annotations

# Yıl -> net aylık asgari ücret (yeni TL)
NET_MINIMUM_WAGE: dict[int, float] = {
    2003: 225.999,
    2004: 303.08,
    2005: 350.15,
    2006: 380.46,
    2007: 403.03,
    2008: 481.55,
    2009: 527.13,
    2010: 576.57,
    2011: 629.96,
    2012: 701.13,
    2013: 773.01,
    2014: 846.00,
    2015: 949.07,
    2016: 1300.99,
    2017: 1404.06,
    2018: 1603.12,
    2019: 2020.90,
    2020: 2324.71,
    2021: 2825.90,
    2022: 4253.40,
    2023: 8506.80,
    2024: 17002.00,
    2025: 22104.67,
    2026: 28075.50,
}


def get(year: int):
    """İlgili yılın net asgari ücretini döner (yoksa None)."""
    return NET_MINIMUM_WAGE.get(year)


def coverage() -> dict:
    years = sorted(NET_MINIMUM_WAGE)
    return {"start": years[0] if years else None, "end": years[-1] if years else None}
