# 💸 TL Enflasyon Hesaplayıcı

> 🌐 **Canlı demo:** **[tl-enflasyon-hesaplayici.vercel.app](https://tl-enflasyon-hesaplayici.vercel.app/)**
> — kurulum gerektirmeden, tarayıcıdan hemen deneyin.

Türk Lirası'nın geçmişten günümüze **alım gücünü** hesaplayan modern bir web uygulaması.
Veriler **TCMB EVDS** (Elektronik Veri Dağıtım Sistemi) servisinden otomatik çekilir ve
önbelleğe alınır. Aylık TÜFE zinciri **Ocak 1964'e** kadar uzanır (bkz. *TÜFE zinciri*).

> **Hesaplama formülü:**
> `Sonuç = Tutar × (Bitiş Tarihi TÜFE Endeksi ÷ Başlangıç Tarihi TÜFE Endeksi)`

---

## ✨ Özellikler

- 🎨 Temiz, **editöryel** arayüz — Tailwind CSS + Fraunces/Inter — **açık/karanlık tema**
  (varsayılan olarak sistem ayarını izler, sağ üstteki düğmeyle değiştirilir, tercih hatırlanır).
- 🖥️ **Tek ekran (kaydırmasız) düzen:** masaüstünde form solda, sonuçlar sağda; her şey görünür alana sığar
  (mobilde sütunlar alt alta gelir).
- 🔢 Türkçe biçimli (₺1.000,50) tutar girişi.
- 📅 Ay/Yıl seçilebilen, **yalnızca veri olan dönemleri** gösteren akıllı tarih seçiciler
  (**1964 – bugün**).
- 📰 **Güncel enflasyon şeridi:** başlığın altında, en son açıklanan aya ait TÜFE, ENAG, İTO,
  Yİ-ÜFE, konut fiyat endeksi ve güncel dolar/euro/altın/BIST/petrol değerleri.
- 🗓️ **Yıllara göre enflasyon tablosu:** 1965'ten bugüne yıl sonu (Aralık→Aralık) TÜFE, ENAG
  ve İTO oranları — tek tıkla açılan bir pencerede.
- 💰 **Eski TL desteği:** 2005 öncesi bir tarih seçildiğinde tutar **eski TL** kabul edilir
  (1.000.000 eski TL = ₺1) ve sonuç doğru para biriminde gösterilir.
- ⚡ Animasyonlu sonuç alanı: büyük TL sonucu, **toplam değişim %** (çok uzun dönemlerde `×`
  çarpanı olarak), çarpan ve TÜFE endeks değerleri.
- 💵 **Çoklu varlık bazında karşılaştırma:** Dolar, Euro, **gram altın**, **Cumhuriyet altını**,
  **BIST 100** ve **Brent petrol** — tutarın başlangıçtaki ve enflasyona göre güncellenen tutarın
  bitişteki birim karşılığı (TCMB verileriyle).
- 🏗️ **Diğer fiyat endeksleri:** Yurt İçi ÜFE (üretici fiyatları), TCMB Konut Fiyat Endeksi ve
  İTO Toptan Eşya Fiyat Endeksi — seçilen dönemdeki toplam değişimleriyle.
- 📉 **Zaman serisi grafiği:** tutarın değerinin aylar boyunca seyri; TÜFE, ENAG ve İTO çizgileri
  bir arada (hafif, bağımsız SVG — ek bağımlılık yok). Değer aralığı 100 katı aşınca
  **logaritmik eksene** geçer, böylece 60 yıllık dönemler de okunabilir kalır.
- 👷 **Asgari ücret karşılaştırması:** "Bu tutar o tarihte kaç net asgari ücretti, bugün kaç?"
- ℹ️ **"Nasıl hesaplandı?" bilgi kutuları:** her karşılaştırma kartının sağ alt köşesindeki **ⓘ**
  düğmesine basınca açılan kutuda; o tarihteki **ham değerler** (ör. *1 gr altın = ₺14 → ₺6.741,91*
  — 2005 öncesi fiyatlar o günün parasıyla), dönemdeki **fiyat artışı** ve artış/azalışın ne anlama
  geldiğine dair kısa bir **iyi/kötü yorumu** gösterilir. Ek olarak:
  - **Dolar / Euro:** o para biriminin **kendi enflasyonu** (ABD TÜFE / Euro Bölgesi HICP —
    yıllık, yaklaşık): *"ABD'de fiyatlar bu dönemde ~%75 arttı; yani dolar kendi içinde ~%43
    değer kaybetti."*
  - **Altın / petrol:** varlığın **dolar cinsinden** değişimi (ons altın, varil Brent) — böylece
    TL fiyatındaki artışın ne kadarı TL'nin erimesi, ne kadarı varlığın kendi değerlenmesi ayrılır.
- 📊 **Reel enflasyon (ENAG):** bağımsız ENAG verisiyle alternatif sonuç (2020+ dönemleri için —
  ENAG Eylül 2020'de kuruldu —, açıkça "bağımsız/doğrulanmamış" etiketiyle).
- 🏛️ **İTO karşılaştırması:** İstanbul Ticaret Odası'nın *Ücretliler Geçinme Endeksi* ile üçüncü
  bir ölçüm — **1964'ten** bugüne, doğrudan TCMB EVDS'den canlı çekilir.
- 🟠 Veri olmayan tarihler / hatalı girişler için kibar, renkli uyarılar.
- 🖼️ **Sonucu paylaş / dışa aktar:** sonucu sosyal medyaya uygun bir görsele (PNG) dönüştürür;
  indirmeden önce **açık/karanlık önizleme** sunar (kişisel ad veya site adresi içermez).
  Üç seçenek: **Paylaş**, **görseli panoya kopyala** (tek tıkla yapıştırmaya hazır; desteklemeyen
  tarayıcıda otomatik indirmeye düşer) ve **görseli indir**.
- 🔄 EVDS'den **otomatik veri çekme + diske önbellekleme** (TTL dolunca yeniler).
- 🛰️ Python **FastAPI** backend hem API'yi hem de frontend'i tek sunucudan servis eder.

---

## 🗂️ Proje Yapısı

```
tlenflasyon/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI uygulaması (API + statik servis)
│   ├── evds.py          # EVDS istemcisi: TÜFE zinciri, varlıklar, endeksler + önbellek
│   ├── enag.py          # ENAG (reel enflasyon) verisi + normalizasyon
│   ├── foreign_cpi.py   # ABD (BLS) + Euro Bölgesi (Eurostat) yıllık enflasyon tablosu
│   └── minwage.py       # Net asgari ücret tablosu (yıllara göre)
├── static/
│   ├── index.html       # Ana arayüz (hesaplayıcı)
│   ├── destek.html      # Destek Ol (Amazon + Chrome eklentisi)
│   ├── gizlilik.html    # Gizlilik politikası
│   ├── kullanim.html    # Kullanım koşulları
│   ├── app.js           # Frontend mantığı + paylaşım görseli
│   ├── theme.js         # Açık/karanlık tema yöneticisi
│   └── styles.css       # Özel stiller + tema (CSS) değişkenleri
├── cache/
│   └── data_cache.json  # Depoya gömülü veri önbelleği (anahtarsız çalışır)
├── baslat.bat           # Windows: tek tıkla kur + çalıştır
├── .env                 # API anahtarınız (gizli — paylaşmayın!)
├── .env.example         # Örnek ortam dosyası
├── requirements.txt
└── README.md
```

---

## 🔑 1. EVDS API Anahtarı (opsiyonel)

> ℹ️ **Anahtar zorunlu değildir.** Depoda güncel veri önbelleği (`cache/data_cache.json`)
> gömülü gelir; projeyi klonlayıp **anahtar olmadan** doğrudan çalıştırabilirsiniz. API anahtarı
> yalnızca verileri **canlı güncellemek** (EVDS'den en yeni ayları çekmek) için gerekir.

Verileri canlı güncellemek isterseniz ücretsiz bir EVDS anahtarı alın:

1. https://evds3.tcmb.gov.tr adresine gidip **ücretsiz üye olun** (e-posta ile aktivasyon).
2. Giriş yaptıktan sonra sağ üstteki **profil/hesap** menüsünden **"API Anahtarı"** bölümüne girin.
3. Verilen anahtarı kopyalayın.
4. Proje kökünde `.env.example` dosyasını `.env` olarak kopyalayın ve anahtarınızı yazın:

   ```env
   EVDS_API_KEY=BURAYA_KENDI_ANAHTARINIZI_YAZIN
   ```

> ⚠️ `.env` dosyası `.gitignore`'a eklidir. Anahtarınızı **asla** herkese açık bir repoya
> yüklemeyin veya başkalarıyla paylaşmayın. Sızdırıldığını düşünüyorsanız EVDS hesabınızdan yenileyin.

---

## 🚀 2. Kurulum ve Çalıştırma (Adım Adım)

> Gereksinim: **Python 3.10+** (bu projede 3.14 ile test edildi).

### ⚡ En kolay yol (Windows): `baslat.bat`

Depoyu indirdikten sonra **`baslat.bat`** dosyasına çift tıklamanız yeterli. İlk çalıştırmada
sanal ortamı kurar, bağımlılıkları yükler ve sunucuyu başlatıp tarayıcıyı açar — **API anahtarı
sormadan**. Gömülü önbellek sayesinde uygulama anında hazır gelir. Sonraki çalıştırmalar saniyeler
içinde başlar.

> İsteğe bağlı: verileri canlı güncellemek isterseniz `.env` dosyasındaki `EVDS_API_KEY` değerini
> doldurmanız yeterli.

Elle kurulum isterseniz aşağıdaki adımları izleyebilirsiniz:

### Windows (PowerShell)

```powershell
# 1) Depoyu klonlayıp klasöre girin
git clone <repo-url> tlenflasyon
cd tlenflasyon

# 2) Sanal ortam (virtual environment) oluşturup aktifleştirin
py -m venv .venv
.\.venv\Scripts\Activate.ps1
#   (Eğer "execution policy" hatası alırsanız bir kez şunu çalıştırın:)
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3) Bağımlılıkları kurun
pip install -r requirements.txt

# 4) API anahtarınızı ayarlayın (.env dosyasını oluşturun)
Copy-Item .env.example .env
#   Ardından .env dosyasını açıp EVDS_API_KEY değerini yazın

# 5) Sunucuyu başlatın
uvicorn app.main:app --reload --port 8000
```

### macOS / Linux (bash)

```bash
git clone <repo-url> tlenflasyon
cd tlenflasyon
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # sonra .env içine EVDS_API_KEY yazın
uvicorn app.main:app --reload --port 8000
```

### 3) Tarayıcıda açın

👉 **http://127.0.0.1:8000**

Veriler depoya gömülü `cache/data_cache.json` dosyasından **anında** yüklenir. Geçerli bir
`EVDS_API_KEY` tanımlıysa ve önbellek eskidiyse, uygulama bir sonraki istekte EVDS'den en güncel
ayları çekip önbelleği tazeler.

> 💡 Sanal ortamı aktifleştirmeden de çalıştırabilirsiniz:
> `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

---

## 🔌 API Uç Noktaları (Endpoints)

| Yöntem | Yol | Açıklama |
|--------|-----|----------|
| `GET`  | `/api/data` | Mevcut TÜFE endeksini, tarih aralığını ve son güncelleme zamanını döner. |
| `POST` | `/api/calculate` | Alım gücü hesaplaması yapar. |
| `POST` | `/api/refresh` | EVDS'den veriyi **zorla** yeniler (cron/Task Scheduler için). |

**Örnek hesaplama isteği:**

```bash
curl -X POST http://127.0.0.1:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"amount":1000,"start_year":2005,"start_month":1,"end_year":2026,"end_month":1}'
```

**Örnek yanıt:**

```json
{
  "amount": 1000.0,
  "result": 32176.0,
  "start_index": 81.18,
  "end_index": 3683.83,
  "start_key": "2005-01",
  "end_key": "2026-01",
  "change_pct": 3117.6,
  "multiplier": 32.176,
  "usd": {
    "rate_start": 1.35,
    "rate_end": 43.1125,
    "usd_start": 740.72,
    "usd_end": 746.33,
    "change_pct": 0.76
  }
}
```

> `usd` alanı: tutarınızın başlangıç tarihindeki dolar değeri (`usd_start`) ile enflasyona göre
> güncellenen tutarın bitiş tarihindeki dolar değerini (`usd_end`) karşılaştırır. Seçilen aylar için
> kur verisi yoksa `usd` alanı `null` döner.
>
> `enag` ve `ito` alanları da benzer biçimde döner (`result`, `change_pct`, `multiplier`, `vs_tufe`);
> ilgili dönem için veri yoksa `null` olur. `enag.verified`, sonucun resmi yıllık orana çapalanıp
> çapalanmadığını belirtir.

---

## 🔄 3. Verinin Güncel Kalması (Otomasyon)

Veri iki şekilde güncel tutulur:

1. **TTL tabanlı otomatik yenileme:** Önbellek `.env` içindeki `CACHE_TTL_SECONDS`
   süresinden (varsayılan 12 saat) eskiyse, bir sonraki istekte EVDS'den otomatik yeniden çekilir.
2. **Manuel/zamanlanmış yenileme:** `POST /api/refresh` uç noktası veriyi anında tazeler.

TÜFE genelde her ayın **3'ünde** açıklanır. Aylık otomatik yenileme için:

### Windows — Görev Zamanlayıcı (Task Scheduler)

Her ayın 4'ünde `/api/refresh` çağıran bir görev oluşturun:

```powershell
$action  = New-ScheduledTaskAction -Execute "curl.exe" -Argument "-X POST http://127.0.0.1:8000/api/refresh"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am   # her gün 09:00 (gün filtresi için aşağıya bakın)
Register-ScheduledTask -TaskName "EVDS-TUFE-Refresh" -Action $action -Trigger $trigger
```

> Yalnızca ayın 4'ünde çalıştırmak için Görev Zamanlayıcı arayüzünden tetikleyiciyi
> "Aylık → ayın 4. günü" olarak ayarlayabilirsiniz.

### Linux/macOS — cron

```bash
crontab -e
# Her ayın 4'ünde saat 09:00'da veriyi yenile:
0 9 4 * * curl -X POST http://127.0.0.1:8000/api/refresh
```

> Not: Sunucu sürekli çalışmıyorsa, TTL mekanizması zaten bir sonraki ilk istekte
> veriyi otomatik tazeleyeceği için cron olmadan da sistem güncel kalır.

---

## 🛠️ Teknik Notlar

- **EVDS yeni servisi:** TCMB, 2024'ten sonra servisi `evds2` → `evds3.tcmb.gov.tr/igmevdsms-dis`
  adresine taşıdı. İstekte parametreler **URL yoluna gömülür** ve API anahtarı `key`
  **HTTP başlığı** ile gönderilir. (`app/evds.py` bu biçimi kullanır.)
- **TÜFE zinciri (Ocak 1964 – bugün):** TÜİK, Ocak 2026'da TÜFE'nin temel yılını **2003=100'den
  2025=100'e** güncelledi; eski `TP.FG.J0` serisi bu tarihte durdu. Uygulama artık 2003=100
  tabanını sürdüren `TP.GENENDEKS.T1` serisini kullanıyor ve EVDS'deki arşiv serilerini bununla
  **zincirliyor** (chain-linking — iki serinin çakıştığı ilk ayda oran alınır):

  | Dönem | Seri | Kaynak |
  |---|---|---|
  | 1964-01 … 1981-12 | `TP.FG.U63` — İTO İstanbul Ücretliler Geçinme Endeksi | İTO — **tahmini** |
  | 1982-01 … 2002-12 | `TP.FG.F01` — TÜFE (1978-79=100, arşiv) | TÜİK (resmi) |
  | 2003-01 … bugün | `TP.GENENDEKS.T1` — TÜFE Genel (2003=100) | TÜİK (resmi) |

  TÜİK'in **aylık** TÜFE'si 1982'de başlar; 1982 öncesi İTO'nun İstanbul endeksiyle uzatılır ve
  API'de `estimated_start` bayrağıyla, arayüzde de açık bir uyarıyla işaretlenir.
- **Paradan altı sıfır atılması (2005):** EVDS'nin tüm fiyat serileri **yeni TL** cinsindendir,
  endeksler ise birimsizdir. Bu yüzden 2005 öncesi bir başlangıç seçildiğinde girilen tutar
  **eski TL** kabul edilip 1.000.000'a bölünür; sonuç ise **bitiş tarihinin** para biriminde
  sunulur. Bilgi kutularındaki ham fiyatlar da ait oldukları dönemin parasıyla gösterilir
  (ör. *1964'te 1 gr altın = 14 TL*, *1 $ = 9 TL*).
- **Varlıklar:** `TP.DK.USD.A.YTL` (dolar), `TP.DK.EUR.A.YTL` (euro), `TP.MK.KUL.YTL` (gram altın),
  `TP.MK.CUM.YTL` (Cumhuriyet altını), `TP.MK.F.BILESIK` (BIST 100), `TP.BRENTPETROL.EUBP`
  (Brent — dolar cinsinden kotalanır, TL fiyatı USD/TL ile çarpılarak bulunur). Ayrıca
  `TP.MK.LON.YTL` (ons altın, USD) varlığın **kendi** değer değişimini göstermek için çekilir.
  Bazı seriler TÜFE'den 1-2 ay geriden geldiği için seçilen ayda veri yoksa **en yakın önceki ay**
  kullanılır (en fazla 6 ay) ve bilgi kutusunda hangi ay olduğu belirtilir.
- **Diğer endeksler:** `TP.TUFE1YI.T1` (Yurt İçi ÜFE, 1982+), `TP.KFE.TR` (TCMB Konut Fiyat
  Endeksi, 2010+), `TP.FG.C01` (İTO Toptan Eşya Fiyat Endeksi, 1968+).
- **"Reel enflasyon" (ENAG):** ENAG'ın herkese açık bir API'si **yoktur** ve resmi sitesi
  (enagrup.org) otomatik erişime kapalıdır (HTTP 525). Bu yüzden ENAG verisi canlı çekilemez;
  [`app/enag.py`](app/enag.py) içinde **aylık oranlar** ENAG'ın basın açıklamalarından derlenerek
  elle tutulur. Basında bulunamayan aylar, ENAG'ın o ay duyurduğu **12 aylık** orandan geriye doğru
  türetilir (`m_t = (1+A_t)/(1+A_{t-1}) × (1+m_{t-12}) − 1`; ± ~0,3 puan hassasiyet). Bu ham veri,
  ENAG'ın geniş kabul gören **yıllık** oranlarına göre yıl bazında **normalize edilir**
  (2020: %36,72 · 2021: %82,81 · 2022: %137,55 · 2023: %127,21 · 2024: %83,40 · 2025: %56,14);
  böylece her yılın bileşik enflasyonu resmi yıllık rakamla birebir tutar. Çapası olmayan dönem
  (içinde bulunulan yıl) ham haliyle kullanılır ve arayüzde
  **"doğrulanmamış"** olarak işaretlenir. ENAG sonucu yalnızca **2020 sonrası** seçimler için
  gösterilir (ENAG Eylül 2020'de kurulduğu için daha eski ENAG verisi yoktur; 2020 Oca–Kas ayları
  doğrulanmış yıllık orana eşit dağıtılmış yaklaşık değerlerdir, Aralık 2020 = %4,08 gerçek değerdir).
  Veriyi güncellemek için `app/enag.py` içindeki `ENAG_MONTHLY_RATES` sözlüğüne yeni ayı ekleyin.

  > ⚠️ **Uyarı:** Normalizasyon yıl sınırlarındaki doğruluğu garanti eder ama yıl içi aylık
  > dağılım yine de yaklaşıktır. ENAG sonuçlarını resmi/kesin veri olarak görmeyin.
- **İTO (İstanbul Ticaret Odası):** Artık topluluk verisi kullanılmıyor — İTO'nun *Ücretliler
  Geçinme Endeksi* (`TP.FG.U63`, **1964'ten** beri kesintisiz) doğrudan **TCMB EVDS'den canlı**
  çekiliyor ve kendi endeksi olarak kullanılıyor. (Eski sürümdeki `app/ito.py` + `ito_data.json`
  "spread" yöntemi bu nedenle kaldırıldı.) İTO resmi bir kurum ölçümüdür, ancak **yalnızca
  İstanbul'u** kapsar — TÜİK'in Türkiye geneli TÜFE'sinin yerine geçmez.
- **Yabancı enflasyon (dolar/euro'nun kendi enflasyonu):** Dolar ve Euro bilgi kutularında, kurun
  TL karşısındaki artışının (**kur artışı**) yanı sıra o para biriminin **kendi** enflasyonu da
  gösterilir — ör. *"ABD'de fiyatlar bu dönemde ~%75 arttı; yani dolar kendi içinde ~%43 değer
  kaybetti."* [`app/foreign_cpi.py`](app/foreign_cpi.py) **resmi yıllık ortalama** oranları tutar:
  ABD için **BLS** (CPI-U, **1950'den**), Euro Bölgesi için **Eurostat** (HICP, **1997'den**).
  Bu veri **yıl bazlıdır** (aylık değil) — bu yüzden arayüzde **"yaklaşık"** etiketlenir;
  oranlardan kümülatif endeks kurulur. 2025 ve öncesi kesinleşmiş yıllık ortalama, **2026
  geçicidir** (yıl tamamlanmadığından o yıl yayımlanan en güncel 12 aylık enflasyon: ABD Haz 2026
  %3,5 · Euro B. Haz 2026 %2,8). Veriyi güncellemek için `foreign_cpi.py` içindeki `_RATES`
  sözlüğüne ekleyin.
  **Altın ve petrol** için bunun yerine varlığın **dolar cinsinden fiyat değişimi** gösterilir
  (ons altın `TP.MK.LON.YTL`, varil Brent) — bir emtianın "kendi enflasyonu" kavramı yoktur,
  ama dolar bazlı seyri TL'nin değer kaybından ayrışmayı gösterir.
- **Sağlamlık:** EVDS'ye ulaşılamazsa uygulama, elindeki (bayat olsa bile) önbelleğe düşer
  ve arayüzde uygun uyarı gösterir.
- **CORS gerekmez:** Frontend ve API aynı sunucudan (aynı origin) servis edildiği için
  ek CORS yapılandırmasına ihtiyaç yoktur.

---

## ❓ Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|-------|-------|
| `Required request header 'key' is not present` | `.env` içindeki `EVDS_API_KEY` boş ya da hatalı. Doğru anahtarı yazın. |
| Açılışta `[UYARI] ... veri yüklenemedi` | İnternet bağlantısını ve API anahtarını kontrol edin; `POST /api/refresh` deneyin. |
| `Activate.ps1 ... çalıştırılamıyor` | PowerShell'de: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Port 8000 dolu | Farklı port: `uvicorn app.main:app --port 8080` |

---

## 📚 Veri Kaynakları ve Sorumluluk Reddi

| Kaynak | Kapsam | Tür |
|--------|--------|-----|
| **TCMB EVDS** — TÜFE (`TP.GENENDEKS.T1` + arşiv serileri, zincirlenmiş) | 1964+ (TÜİK: 1982+) | Resmi (canlı API) |
| **TCMB EVDS** — USD (1960+), EUR (1999+), gram altın (1960+), Cumhuriyet altını (1960+), BIST 100 (1986+), Brent petrol (1987+) | değişken | Resmi (canlı API) |
| **TCMB EVDS** — Yİ-ÜFE (1982+), Konut Fiyat Endeksi (2010+), İTO Toptan Eşya (1968+) | değişken | Resmi (canlı API) |
| **İTO** (İstanbul Ticaret Odası) — Ücretliler Geçinme Endeksi (`TP.FG.U63`) | 1964+ | Resmi kurum ölçümü — yalnızca İstanbul |
| **ENAG** (Enflasyon Araştırma Grubu) | 2020+ | Bağımsız — basın açıklamalarından derlenir, yıllık orana normalize |
| **Net asgari ücret** (`app/minwage.py`) | 2003+ | Kamuya açık yıllık tablo (Ocak değerleri) |
| **ABD TÜFE** (BLS, CPI-U) · **Euro Bölgesi HICP** (Eurostat) — `app/foreign_cpi.py` | 1950+ / 1997+ | Resmi yıllık ortalama oranlar (elle tutulur, yıl bazlı/yaklaşık) |

ENAG aylık oranları ve yıllık çapaları için ENAG'ın kamuya açık açıklamaları kullanılmıştır.

> ⚠️ **Sorumluluk reddi:** Bu uygulama yalnızca **bilgilendirme/eğitim** amaçlıdır. ENAG sonuçları
> bağımsız tahminlerdir, İTO yalnızca İstanbul'u kapsar ve 1982 öncesi TÜFE tahminidir — hiçbiri
> TÜİK'in resmi Türkiye enflasyonu değildir ve doğruluğu garanti edilmez. Yatırım veya hukuki
> kararlar için resmi TÜİK/TCMB verilerini esas alın.

## 🤝 Katkı

Katkılar memnuniyetle karşılanır. ENAG verisini güncellemek için
[`app/enag.py`](app/enag.py), asgari ücret için [`app/minwage.py`](app/minwage.py), yabancı
enflasyon için [`app/foreign_cpi.py`](app/foreign_cpi.py) dosyalarını düzenleyebilirsiniz
(diğer tüm veriler EVDS'den canlı gelir). Hata bildirimi ve öneriler için issue açabilirsiniz.

## 📄 Lisans

[MIT Lisansı](LICENSE) altında yayımlanmıştır. Dilediğiniz gibi kullanabilir, değiştirebilir ve
dağıtabilirsiniz.

---

<sub>TCMB EVDS bir Türkiye Cumhuriyet Merkez Bankası hizmetidir. Bu proje TCMB, ENAG veya İTO ile
resmi olarak bağlantılı değildir.</sub>
