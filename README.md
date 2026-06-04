# 💸 TL Enflasyon Hesaplayıcı

> 🌐 **Canlı demo:** **[tl-enflasyon-hesaplayici.vercel.app](https://tl-enflasyon-hesaplayici.vercel.app/)**
> — kurulum gerektirmeden, tarayıcıdan hemen deneyin.

Türk Lirası'nın geçmişten günümüze **alım gücünü** hesaplayan modern bir web uygulaması.
Veriler **TCMB EVDS** (Elektronik Veri Dağıtım Sistemi) servisinden, **TÜFE Genel Endeks
(2003=100)** serisi (`TP.FG.J0`) kullanılarak otomatik çekilir ve önbelleğe alınır.

> **Hesaplama formülü:**
> `Sonuç = Tutar × (Bitiş Tarihi TÜFE Endeksi ÷ Başlangıç Tarihi TÜFE Endeksi)`

---

## ✨ Özellikler

- 🎨 Temiz, **editöryel** arayüz — Tailwind CSS + Fraunces/Inter — **açık/karanlık tema**
  (varsayılan olarak sistem ayarını izler, sağ üstteki düğmeyle değiştirilir, tercih hatırlanır).
- 🖥️ **Tek ekran (kaydırmasız) düzen:** masaüstünde form solda, sonuçlar sağda; her şey görünür alana sığar
  (mobilde sütunlar alt alta gelir).
- 🔢 Türkçe biçimli (₺1.000,50) tutar girişi.
- 📅 Ay/Yıl seçilebilen, **yalnızca veri olan dönemleri** gösteren akıllı tarih seçiciler.
- ⚡ Animasyonlu sonuç alanı: büyük TL sonucu, **toplam değişim %**, çarpan ve TÜFE endeks değerleri.
- 💵 **Çoklu varlık bazında karşılaştırma:** Dolar, Euro ve **gram altın** — tutarın başlangıçtaki
  ve enflasyona göre güncellenen tutarın bitişteki birim/gram karşılığı (TCMB kurları ile).
- 📉 **Zaman serisi grafiği:** tutarın değerinin aylar boyunca seyri; TÜFE, ENAG ve İTO çizgileri
  bir arada (hafif, bağımsız SVG — ek bağımlılık yok).
- 👷 **Asgari ücret karşılaştırması:** "Bu tutar o tarihte kaç net asgari ücretti, bugün kaç?"
- 📊 **Reel enflasyon (ENAG):** bağımsız ENAG verisiyle alternatif sonuç (2020+ dönemleri için —
  ENAG Eylül 2020'de kuruldu —, açıkça "bağımsız/doğrulanmamış" etiketiyle).
- 🏛️ **İTO karşılaştırması:** İstanbul Ticaret Odası endeksiyle üçüncü bir ölçüm (2003+). Resmi TÜFE'ye
  İTO–TÜİK farkı uygulanarak hesaplanır; böylece resmi veri bel kemiği kalır.
- 🟠 Veri olmayan tarihler / hatalı girişler için kibar, renkli uyarılar.
- 🖼️ **Sonucu paylaş / dışa aktar:** sonucu sosyal medyaya uygun bir görsele (PNG) dönüştürür;
  indirmeden önce **açık/karanlık önizleme** sunar (kişisel ad veya site adresi içermez).
- 🔄 EVDS'den **otomatik veri çekme + diske önbellekleme** (TTL dolunca yeniler).
- 🛰️ Python **FastAPI** backend hem API'yi hem de frontend'i tek sunucudan servis eder.

---

## 🗂️ Proje Yapısı

```
tlenflasyon/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI uygulaması (API + statik servis)
│   ├── evds.py          # EVDS istemcisi (TÜFE + USD/EUR/altın) + önbellek
│   ├── enag.py          # ENAG (reel enflasyon) verisi + normalizasyon
│   ├── ito.py           # İTO endeksi (spread yöntemi)
│   ├── minwage.py       # Net asgari ücret tablosu (yıllara göre)
│   └── data/
│       └── ito_data.json  # İTO/TÜİK topluluk verisi (aylık oranlar)
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
- **Seriler:** TÜFE için `TP.FG.J0` (**2003=100**, aylık), dolar karşılaştırması için
  `TP.DK.USD.A.YTL` (USD/TL döviz alış, aylık ortalama). Her ikisi de **Ocak 2003'ten**
  itibaren mevcuttur. Daha eski yıllar için TÜİK'in farklı bazlı serilerinin (1994=100 vb.)
  zincirlenmesi gerekir — bu sürümde kapsanmamıştır.
- **"Reel enflasyon" (ENAG):** ENAG'ın herkese açık bir API'si **yoktur** ve resmi sitesi
  (enagrup.org) otomatik erişime kapalıdır (HTTP 525). Bu yüzden ENAG verisi canlı çekilemez;
  [`app/enag.py`](app/enag.py) içinde **topluluk kaynaklı aylık oranlar** elle tutulur
  (kaynak: `github.com/muslumyalcin-git/enflasyon-matrix`). Bu ham veri, ENAG'ın geniş kabul
  gören **yıllık** oranlarına göre yıl bazında **normalize edilir** (2020: %36,72 · 2021: %82,81 ·
  2022: %137,55 · 2023: %127,21 · 2024: %83,40); böylece her yılın bileşik enflasyonu resmi yıllık
  rakamla birebir tutar. Çapası olmayan dönemler (2025–2026) ham haliyle kullanılır ve arayüzde
  **"doğrulanmamış"** olarak işaretlenir. ENAG sonucu yalnızca **2020 sonrası** seçimler için
  gösterilir (ENAG Eylül 2020'de kurulduğu için daha eski ENAG verisi yoktur; 2020 Oca–Kas ayları
  doğrulanmış yıllık orana eşit dağıtılmış yaklaşık değerlerdir, Aralık 2020 = %4,08 gerçek değerdir).
  Veriyi güncellemek için `app/enag.py` içindeki `ENAG_MONTHLY_RATES` sözlüğüne yeni ayı ekleyin.

  > ⚠️ **Uyarı:** Ham topluluk verisi, ENAG'ın yıllık oranlarıyla doğrudan tutmuyordu
  > (2021'de +14, 2024'te −17 puan sapma). Normalizasyon yıl sınırlarındaki doğruluğu garanti eder
  > ama yıl içi aylık dağılım yine de yaklaşıktır. ENAG sonuçlarını resmi/kesin veri olarak görmeyin.
- **İTO (İstanbul Ticaret Odası):** Aylık veri 2003'ten beri mevcuttur ancak ham topluluk verisinin
  mutlak değerleri eski yıllarda resmi TÜFE'den sapıyordu (~%17). Bu yüzden [`app/ito.py`](app/ito.py)
  **"spread" yöntemini** kullanır: aynı derlemedeki İTO ve TÜİK serilerinin oranı (İTO–TÜİK farkı)
  alınır ve **resmi TÜFE (EVDS) üzerine uygulanır**. Ortak sapma oranda birbirini götürdüğü için
  eski yıllardaki hata büyük ölçüde düzelir; resmi TÜFE bel kemiği olarak kalır. İTO da bağımsız/
  topluluk kaynaklıdır, resmi rakam değildir. (Not: İTO Ocak 2025'te 2023=100 bazına geçti; oranlar
  baz bağımsız olduğundan hesap etkilenmez.)
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
| **TCMB EVDS** — TÜFE (`TP.FG.J0`), USD (`TP.DK.USD.A.YTL`), EUR (`TP.DK.EUR.A.YTL`), gram altın (`TP.MK.KUL.YTL`) | 2003+ | Resmi (canlı API) |
| **ENAG** (Enflasyon Araştırma Grubu) | 2020+ | Bağımsız — topluluk kaynaklı, yıllık orana normalize |
| **İTO** (İstanbul Ticaret Odası) | 2003+ | Bağımsız — topluluk kaynaklı, spread yöntemiyle |
| **Net asgari ücret** (`app/minwage.py`) | 2003+ | Kamuya açık yıllık tablo (Ocak değerleri) |

ENAG ve İTO için kullanılan aylık veriler topluluk derlemesinden alınmıştır
([github.com/muslumyalcin-git/enflasyon-matrix](https://github.com/muslumyalcin-git/enflasyon-matrix));
ENAG yıllık çapaları için kamuya açık ENAG rakamları kullanılmıştır.

> ⚠️ **Sorumluluk reddi:** Bu uygulama yalnızca **bilgilendirme/eğitim** amaçlıdır. ENAG ve İTO
> sonuçları bağımsız/topluluk kaynaklı tahminlerdir, resmi rakam değildir ve doğruluğu garanti
> edilmez. Yatırım veya hukuki kararlar için resmi TÜİK/TCMB verilerini esas alın.

## 🤝 Katkı

Katkılar memnuniyetle karşılanır. ENAG/İTO verisini güncellemek için
[`app/enag.py`](app/enag.py) ve [`app/data/ito_data.json`](app/data/ito_data.json) dosyalarını
düzenleyebilirsiniz. Hata bildirimi ve öneriler için issue açabilirsiniz.

## 📄 Lisans

[MIT Lisansı](LICENSE) altında yayımlanmıştır. Dilediğiniz gibi kullanabilir, değiştirebilir ve
dağıtabilirsiniz.

---

<sub>TCMB EVDS bir Türkiye Cumhuriyet Merkez Bankası hizmetidir. Bu proje TCMB, ENAG veya İTO ile
resmi olarak bağlantılı değildir.</sub>
