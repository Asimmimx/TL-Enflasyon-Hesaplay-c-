@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title TL Enflasyon Hesaplayici

echo ==================================================
echo    TL Enflasyon Hesaplayici - Baslatici
echo ==================================================
echo.

REM --- 1) Python sanal ortami (.venv) ---
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Python sanal ortami olusturuluyor...
    where py >nul 2>nul
    if !errorlevel!==0 (
        py -m venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo   HATA: Python bulunamadi veya sanal ortam olusturulamadi.
        echo   Lutfen Python 3.10+ kurun: https://www.python.org/downloads/
        echo   ^(Kurulumda "Add Python to PATH" secenegini isaretleyin.^)
        echo.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Sanal ortam mevcut.
)

REM --- 2) Bagimliliklar (yalnizca ilk kurulumda) ---
if not exist ".venv\.setup_done" (
    echo [2/3] Bagimliliklar kuruluyor... ^(ilk calistirmada birkac dakika surebilir^)
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo.
        echo   HATA: Bagimliliklar kurulamadi. Internet baglantinizi kontrol edip
        echo   baslat.bat dosyasini tekrar calistirin.
        echo.
        pause
        exit /b 1
    )
    echo done> ".venv\.setup_done"
) else (
    echo [2/3] Bagimliliklar zaten kurulu.
)

REM --- (Opsiyonel) .env: API anahtari ZORUNLU DEGIL ---
REM Veri onbellegi (cache\data_cache.json) depoya gomulu oldugundan uygulama
REM anahtar olmadan da calisir. .env yoksa ornekten sessizce olusturulur;
REM anahtari yalnizca verileri CANLI guncellemek isteyenler doldurur.
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)

REM --- 3) Sunucuyu baslat + tarayiciyi ac ---
echo [3/3] Sunucu baslatiliyor: http://127.0.0.1:8000
echo       ^(Durdurmak icin bu pencerede Ctrl+C yapin^)
echo.
echo   Not: Uygulama API anahtari olmadan da calisir ^(veriler hazir gelir^).
echo        En guncel veriyi EVDS'den cekmek isterseniz .env icindeki
echo        EVDS_API_KEY satirina ucretsiz anahtarinizi yazabilirsiniz.
echo        Anahtar almak icin: https://evds3.tcmb.gov.tr
echo.

REM Tarayiciyi ~3 sn sonra (sunucu ayaga kalkinca) ac
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:8000"

".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000

echo.
echo Sunucu durduruldu.
pause
