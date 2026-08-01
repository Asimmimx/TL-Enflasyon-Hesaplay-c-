// TL Enflasyon Hesaplayıcı — frontend mantığı

const MONTHS_TR = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

const tlFormatter = new Intl.NumberFormat('tr-TR', {
  style: 'currency', currency: 'TRY', maximumFractionDigits: 2,
});
const numFormatter = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 2 });
const usdFormatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const usd = (v) => '$' + usdFormatter.format(v);

// Yüzde metni. Çok büyük değişimlerde (%1.000+) yüzde okunaksızlaşır; onun yerine
// "1.234×" biçimi kullanılır — 1970'lerden bugüne gibi dönemlerde tek çare bu.
function fmtChange(v) {
  if (v == null) return '—';
  if (Math.abs(v) >= 900) return `${numFormatter.format(1 + v / 100)}×`;
  return `%${numFormatter.format(v)}`;
}
function fmtChangeSigned(v) {
  if (v == null) return '—';
  if (Math.abs(v) >= 900) return `${numFormatter.format(1 + v / 100)}×`;
  // İşaret yüzde imgesinin önüne gelir: "-%92,17" ("%-92,17" değil).
  return `${v >= 0 ? '+' : '−'}%${numFormatter.format(Math.abs(v))}`;
}

// Endeks değerleri 1964'te 0,0000011 gibi çok küçük olabilir; anlamlı basamakları koru.
const smallNumFormatter = new Intl.NumberFormat('tr-TR', { maximumSignificantDigits: 4 });
function fmtIndex(v) {
  if (v == null) return '—';
  return Math.abs(v) >= 1 ? numFormatter.format(v) : smallNumFormatter.format(v);
}

// Paradan altı sıfır atılması (1 Ocak 2005): öncesindeki tutarlar "eski TL"dir.
const REDENOMINATION_YEAR = 2005;

const el = (id) => document.getElementById(id);
const amountInput = el('amount');
const startMonth = el('startMonth');
const startYear = el('startYear');
const endMonth = el('endMonth');
const endYear = el('endYear');
const calcBtn = el('calcBtn');
const calcBtnText = el('calcBtnText');
const calcSpinner = el('calcSpinner');
const alertBox = el('alertBox');
const alertText = el('alertText');
const exportBtn = el('exportBtn');

let DATA = { values: {}, byYear: {} };

// Sonuç kartındaki chip düzeni: ilk dört sabit kutu, kalanı "daha fazla" bölümünde.
const PRIMARY_ASSETS = [['usd', 'usdChip'], ['eur', 'eurChip'], ['gold', 'goldChip']];
const MORE_ASSETS = ['cgold', 'bist', 'brent'];
let lastResult = null; // { amount, payload, data } — dışa aktarma için son hesaplama
let shareTheme = 'light'; // paylaşım görselinin teması (modal içinde seçilir)

// ---------- Yardımcılar ----------

function showAlert(message, type = 'warning') {
  alertText.textContent = message;
  alertBox.className =
    'mt-3 flex items-start gap-2.5 rounded-lg border px-4 py-2.5 text-[13px] leading-snug ' +
    (type === 'error'
      ? 'border-down/30 bg-down/5 text-down'
      : 'border-[#caa54a]/40 bg-[#f3e7c2]/40 text-[#8a6d1f]');
}
function hideAlert() {
  alertBox.className = 'mt-3 hidden';
}

function setLoading(loading) {
  calcBtn.disabled = loading;
  calcSpinner.classList.toggle('hidden', !loading);
  calcBtnText.textContent = loading ? 'Hesaplanıyor…' : 'Hesapla';
}

function parseAmount(str) {
  if (!str) return NaN;
  const cleaned = String(str).replace(/\./g, '').replace(',', '.').replace(/[^\d.]/g, '');
  return parseFloat(cleaned);
}

const monthLabel = (m, y) => `${MONTHS_TR[m - 1]} ${y}`;

// ---------- Dropdown doldurma ----------

function buildSelectors() {
  const keys = Object.keys(DATA.values).sort();
  if (keys.length === 0) return;

  const byYear = {};
  for (const key of keys) {
    const [y, m] = key.split('-').map(Number);
    (byYear[y] ||= []).push(m);
  }
  DATA.byYear = byYear;
  const years = Object.keys(byYear).map(Number).sort((a, b) => a - b);

  for (const sel of [startYear, endYear]) {
    sel.innerHTML = '';
    for (const y of years) {
      const opt = document.createElement('option');
      opt.value = y; opt.textContent = y;
      sel.appendChild(opt);
    }
  }
  startYear.value = years[0];
  endYear.value = years[years.length - 1];
  refreshMonths(startMonth, startYear.value, 'first');
  refreshMonths(endMonth, endYear.value, 'last');
  updateAmountHint();
}

// 2005'te paradan altı sıfır atıldı. Başlangıç tarihi 2005'ten eskiyse girilen tutar
// "eski TL" kabul edilir; kullanıcı bunu bilmeli.
function updateAmountHint() {
  const year = Number(startYear.value);
  const isOld = year && year < REDENOMINATION_YEAR;
  el('amountHint').classList.toggle('hidden', !isOld);
  if (isOld) {
    el('amountHint').textContent =
      `${year} için tutarı o günün parasıyla (eski TL) girin — 2005'te paradan altı sıfır ` +
      `atıldı, 1.000.000 eski TL = ₺1.`;
  }
}

function refreshMonths(monthSel, year, defaultPos) {
  const available = (DATA.byYear[year] || []).slice().sort((a, b) => a - b);
  const previous = Number(monthSel.value);
  monthSel.innerHTML = '';
  for (const m of available) {
    const opt = document.createElement('option');
    opt.value = m; opt.textContent = MONTHS_TR[m - 1];
    monthSel.appendChild(opt);
  }
  if (available.includes(previous)) monthSel.value = previous;
  else if (defaultPos === 'last') monthSel.value = available[available.length - 1];
  else monthSel.value = available[0];
}

// ---------- Hesaplama ----------

async function calculate() {
  hideAlert();
  const amount = parseAmount(amountInput.value);
  if (!amount || amount <= 0) {
    showAlert('Lütfen geçerli bir tutar girin.', 'warning');
    return;
  }
  const payload = {
    amount,
    start_year: Number(startYear.value),
    start_month: Number(startMonth.value),
    end_year: Number(endYear.value),
    end_month: Number(endMonth.value),
  };

  setLoading(true);
  try {
    const resp = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) {
      showAlert(data.detail || 'Hesaplama yapılamadı.', resp.status === 404 ? 'warning' : 'error');
      return;
    }
    renderResult(amount, payload, data);
  } catch (err) {
    showAlert('Sunucuya bağlanılamadı. Backend çalışıyor mu?', 'error');
  } finally {
    setLoading(false);
  }
}

// Grafik çizgi renkleri site temasından (CSS değişkenleri) okunur — karanlık temada da okunaklı.
function cssRGB(varName) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return v ? `rgb(${v})` : '#1c1b18';
}
function seriesColors() {
  return { tufe: cssRGB('--c-ink'), ito: cssRGB('--c-ito'), enag: cssRGB('--c-accent') };
}

// Paylaşım görseli (PNG) için sabit paletler — modal'da seçilen temaya göre uygulanır.
const SHARE_PALETTES = {
  light: { paper: '#f6f4ef', ink: '#1c1b18', soft: '#5c574e', line: '#e6e1d7', accent: '#b3402f', up: '#166534', tufe: '#1c1b18', ito: '#2f6f9f', enag: '#b3402f' },
  dark:  { paper: '#181714', ink: '#ede9e1', soft: '#a8a195', line: '#3a3630', accent: '#e27c63', up: '#6ebe86', tufe: '#ede9e1', ito: '#6ea6d6', enag: '#e27c63' },
};

const monthShort = (key) => {
  const [y, m] = key.split('-').map(Number);
  return `${MONTHS_TR[m - 1].slice(0, 3)} ${y}`;
};

function renderResult(amount, payload, data) {
  lastResult = { amount, payload, data };
  el('emptyState').classList.add('hidden');
  el('resultContent').classList.remove('hidden');

  const startLabel = monthLabel(payload.start_month, payload.start_year);
  const endLabel = monthLabel(payload.end_month, payload.end_year);
  el('resultRange').textContent = `${startLabel} → ${endLabel}`;

  // Resmi (TÜFE)
  const v = el('resultValue');
  v.textContent = tlFormatter.format(data.result);
  v.classList.remove('animate-pop'); void v.offsetWidth; v.classList.add('animate-pop');

  const up = data.change_pct >= 0;
  const ce = el('resultChange');
  ce.className = 'inline-flex items-center gap-1 text-xl font-700 tabular-nums ' + (up ? 'text-down' : 'text-up');
  ce.innerHTML = `<span>${up ? '▲' : '▼'}</span><span>${fmtChange(Math.abs(data.change_pct))}</span>`;

  // Sonucun para birimi bitiş tarihine göredir; 2005 öncesiyse "eski TL" olduğunu belirt.
  el('resultLabel').textContent = data.old_lira_end
    ? 'Resmi (TÜFE) karşılığı — eski TL' : 'Resmi (TÜFE) karşılığı';

  el('resultMultiplier').textContent = `${numFormatter.format(data.multiplier)}×`;
  el('resultIndices').textContent = `${fmtIndex(data.start_index)} → ${fmtIndex(data.end_index)}`;

  // Grafik + açıklama (TÜFE / ENAG / İTO)
  renderChartLegend(data);
  drawChart(data.series);
  el('chartStart').textContent = monthShort(data.start_key);
  el('chartEnd').textContent = monthShort(data.end_key);

  // Birim bazında karşılaştırmalar
  const a = data.assets || {};
  // Açılır bilgi kutusunun ("nasıl hesaplandı?") ihtiyaç duyduğu ortak bağlam.
  const infoCtx = {
    startLabel, endLabel,
    startYear: payload.start_year, endYear: payload.end_year,
    amount, result: data.result,
    startKey: data.start_key, endKey: data.end_key,
  };
  for (const [key, id] of PRIMARY_ASSETS) renderAssetChip(id, a[key], infoCtx);
  renderMinwageChip(data.minwage, payload, infoCtx);
  renderMoreSection(data, infoCtx);

  // Uyarı notu
  const notes = [];
  if (data.old_lira_start) {
    notes.push(data.old_lira_end
      ? 'Tutar ve sonuç, o dönemin parası (eski TL) cinsindendir.'
      : 'Tutar eski TL kabul edildi; sonuç bugünkü TL cinsindendir.');
  }
  if (data.estimated_start && data.official_start) {
    notes.push(
      `${data.official_start.slice(0, 4)} öncesi için TÜİK'in aylık TÜFE'si yoktur; ` +
      'o dönem İTO İstanbul endeksiyle uzatılmıştır (tahmini).');
  }
  notes.push('İTO İstanbul’u kapsar, ENAG bağımsızdır — ikisi de resmi Türkiye enflasyonu değildir.');
  if (data.series && data.series.enag) notes.push('ENAG çizgisi Eylül 2020 sonrasını kapsar.');
  el('caveat').innerHTML =
    `<span class="inline-flex items-start gap-1.5">` +
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="mt-px h-3.5 w-3.5 shrink-0 opacity-70">` +
    `<circle cx="12" cy="12" r="9" /><path stroke-linecap="round" d="M12 11v5M12 7.5h.01" /></svg>` +
    `<span>${notes.join(' ')}</span></span>`;
}

function renderChartLegend(data) {
  // Çizilen serilerle birebir uyumlu olsun diye değerleri series'in son noktasından al.
  const s = data.series || {};
  const lastVal = (arr) => {
    if (!arr) return null;
    for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return arr[i];
    return null;
  };
  const SC = seriesColors();
  const items = [];
  const t = lastVal(s.tufe);
  if (t != null) items.push({ label: 'TÜFE', color: SC.tufe, val: t });
  const e = lastVal(s.enag);
  if (e != null) items.push({ label: 'ENAG*', color: SC.enag, val: e });
  const i = lastVal(s.ito);
  if (i != null) items.push({ label: 'İTO*', color: SC.ito, val: i });

  el('chartLegend').innerHTML = items.map((it) =>
    `<span class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full" style="background:${it.color}"></span>` +
    `${it.label} <span class="font-700 tabular-nums">${tlFormatter.format(it.val)}</span></span>`
  ).join('');
}

// Varlığın "kaç birim" biçimi: altın gram, dolar/euro sembol önde, diğerleri birim sonda.
function unitFormatter(asset) {
  if (asset.kind === 'currency') return (x) => `${asset.symbol}${numFormatter.format(x)}`;
  return (x) => `${numFormatter.format(x)} ${asset.symbol}`;
}

function assetChipInner(asset, ctx) {
  const fmt = unitFormatter(asset);
  const pos = asset.change_pct >= 0;
  return (
    `<div class="flex items-center justify-between text-[12px]">
       <span class="font-600">${asset.label}</span>
       <span class="font-700 tabular-nums ${pos ? 'text-up' : 'text-down'}">${fmtChangeSigned(asset.change_pct)}</span>
     </div>
     <div class="mt-0.5 pr-7 text-[13px] tabular-nums">${fmt(asset.unit_start)} <span class="text-ink-soft">→</span> ${fmt(asset.unit_end)}</div>` +
    chipInfoBlock(assetPopHTML(asset, ctx))
  );
}

function renderAssetChip(id, asset, ctx) {
  const chip = el(id);
  if (!asset) { chip.classList.add('hidden'); return; }
  chip.classList.remove('hidden');
  chip.innerHTML = assetChipInner(asset, ctx);
}

// "Daha fazla" bölümü: ek varlık chip'leri + diğer fiyat endeksleri (ÜFE, konut, toptan eşya).
function renderMoreSection(data, ctx) {
  const assets = data.assets || {};
  const extra = MORE_ASSETS.filter((k) => assets[k]);
  el('moreChips').innerHTML = extra
    .map((k) => `<div class="chip">${assetChipInner(assets[k], ctx)}</div>`)
    .join('');

  const indicators = data.indicators || {};
  const keys = Object.keys(indicators);
  el('indicatorList').innerHTML = keys.map((k) => {
    const it = indicators[k];
    const pos = it.change_pct >= 0;
    return (
      `<div class="ind-row">
         <span>${it.label} <span class="ind-hint">${it.hint}</span></span>
         <span class="font-700 tabular-nums ${pos ? 'text-down' : 'text-up'}">${fmtChange(it.change_pct)}</span>
       </div>`
    );
  }).join('');

  // Gösterilecek hiçbir şey yoksa açma düğmesini gizle.
  const empty = extra.length === 0 && keys.length === 0;
  el('moreToggle').classList.toggle('hidden', empty);
  if (empty) setMoreOpen(false);
}

function setMoreOpen(open) {
  el('moreSection').classList.toggle('hidden', !open);
  el('moreToggle').setAttribute('aria-expanded', String(open));
  el('moreToggleText').textContent = open ? 'Gizle' : 'Diğer varlıklar ve göstergeler';
}

function renderMinwageChip(m, payload, ctx) {
  const chip = el('minwageChip');
  if (!m) { chip.classList.add('hidden'); return; }
  chip.classList.remove('hidden');
  const pos = m.change_pct >= 0;
  // O dönemin gerçek net asgari ücretleri (yıl başı). Backend wage_start/wage_end döner.
  const hasWages = m.wage_start != null && m.wage_end != null;
  const wageLine = hasWages
    ? `<div class="mt-0.5 pr-7 text-[11px] tabular-nums text-ink-soft">${payload.start_year}: ${tlFormatter.format(m.wage_start)} <span>→</span> ${payload.end_year}: ${tlFormatter.format(m.wage_end)} <span class="not-italic">(yıl başı net)</span></div>`
    : '';
  chip.innerHTML =
    `<div class="flex items-center justify-between text-[12px]">
       <span class="font-600">Asgari ücret</span>
       <span class="font-700 tabular-nums ${pos ? 'text-up' : 'text-down'}">${fmtChangeSigned(m.change_pct)}</span>
     </div>
     <div class="mt-0.5 ${hasWages ? '' : 'pr-7 '}text-[13px] tabular-nums">${numFormatter.format(m.ratio_start)} <span class="text-ink-soft">→</span> ${numFormatter.format(m.ratio_end)} maaş</div>
     ${wageLine}` +
    (hasWages ? chipInfoBlock(minwagePopHTML(m, ctx)) : '');
}

// ---------- Chip "nasıl hesaplandı?" açılır bilgi kutusu ----------

// Daire içinde "i" düğmesi + (gizli) açılır kutu. İçerik popBody'den gelen HTML'dir.
function chipInfoBlock(bodyHTML) {
  return (
    `<button type="button" class="chip-info" aria-label="Nasıl hesaplandı?" aria-expanded="false">` +
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">` +
    `<circle cx="12" cy="12" r="9" /><path stroke-linecap="round" d="M12 11v5M12 7.5h.01" /></svg>` +
    `</button>` +
    `<div class="chip-pop hidden" role="tooltip">${bodyHTML}</div>`
  );
}

// Açılır kutunun ortak gövdesi: başlık · ham değer satırları · "kendi enflasyonu" notu ·
// ayraç · hesaplama cümlesi · iyi/kötü yorumu (artış/azalış rengiyle).
function popBody(title, rows, noteHTML, calcLine, verdict, pos) {
  return (
    `<p class="chip-pop-title">${title}</p>` +
    `<div class="chip-pop-rows">${rows}</div>` +
    `<p class="chip-pop-note">${noteHTML}</p>` +
    `<div class="chip-pop-sep"></div>` +
    `<p class="chip-pop-calc">${calcLine}</p>` +
    `<p class="chip-pop-verdict ${pos ? 'text-up' : 'text-down'}">${verdict}</p>`
  );
}

// "1 $" / "1 gr altın" / "1 varil Brent petrol" — fiyat satırlarında kullanılan birim adı.
function priceUnitLabel(asset) {
  if (asset.kind === 'currency') return `1 ${asset.symbol}`;
  return `1 ${asset.symbol} ${asset.label.toLowerCase()}`;
}

// Dolar / Euro / Altın / Cumhuriyet altını / BIST / Brent açılır kutusunun içeriği.
function assetPopHTML(asset, ctx) {
  const isCurrency = asset.kind === 'currency';
  // price_start/price_end kendi dönemlerinin para biriminde; artış oranı backend'den gelir.
  const rise = asset.price_change_pct;
  const riseVerb = rise >= 0 ? 'arttı' : 'azaldı';
  const pos = asset.change_pct >= 0;
  const pctAbs = fmtChange(Math.abs(asset.change_pct));
  const fmt = unitFormatter(asset);
  const priceLabel = priceUnitLabel(asset);

  // Fiyat serisi seçilen ayda yoksa en yakın önceki ay kullanılır — hangisi olduğunu göster.
  const monthNote = (key, fallbackKey) =>
    (fallbackKey && fallbackKey !== key) ? ` <span class="ind-hint">(${monthShort(fallbackKey)})</span>` : '';

  const rows =
    `<div class="chip-pop-row"><span>${ctx.startLabel}${monthNote(ctx.startKey, asset.price_start_key)}</span>` +
    `<span>${priceLabel} = ${tlFormatter.format(asset.price_start)}</span></div>` +
    `<div class="chip-pop-row"><span>${ctx.endLabel}${monthNote(ctx.endKey, asset.price_end_key)}</span>` +
    `<span>${priceLabel} = ${tlFormatter.format(asset.price_end)}</span></div>`;

  const riseLine = isCurrency
    ? `${asset.label}/TL bu dönemde ${fmtChange(Math.abs(rise))} ${riseVerb} (kur artışı).`
    : `${asset.label} fiyatı TL cinsinden ${fmtChange(Math.abs(rise))} ${riseVerb}.`;

  // Para biriminin "kendi" enflasyonu (ABD TÜFE / Euro Bölgesi HICP) — backend'den gelirse.
  let extraLine = '';
  if (asset.cpi_change_pct != null) {
    const c = asset.cpi_change_pct;
    const cAbs = fmtChange(Math.abs(c));
    if (c >= 0) {
      const loss = (1 - 1 / (1 + c / 100)) * 100; // birimin kendi alım gücü kaybı
      extraLine =
        `<span class="chip-pop-foreign">${asset.cpi_region}'de fiyatlar bu dönemde ~${cAbs} arttı; ` +
        `yani ${asset.label.toLowerCase()} kendi içinde ~%${numFormatter.format(loss)} değer kaybetti (yıllık, yaklaşık).</span>`;
    } else {
      extraLine = `<span class="chip-pop-foreign">${asset.cpi_region}'de fiyatlar bu dönemde ~${cAbs} azaldı (yıllık, yaklaşık).</span>`;
    }
  } else if (asset.usd_change_pct != null) {
    // Altın/petrol: TL fiyatındaki artışın ne kadarı TL'nin erimesi, ne kadarı varlığın
    // kendi değerlenmesi? Dolar cinsinden fiyat bunu ayırır.
    const u = asset.usd_change_pct;
    extraLine =
      `<span class="chip-pop-foreign">Dolar cinsinden (${asset.usd_unit}) fiyatı ise ` +
      `${fmtChange(Math.abs(u))} ${u >= 0 ? 'arttı' : 'azaldı'} — artışın bu kısmı TL'nin ` +
      `değer kaybından değil, varlığın kendi hareketinden gelir.</span>`;
  }
  const noteHTML = riseLine + extraLine;

  const calcLine = isCurrency
    ? `${tlFormatter.format(ctx.amount)} o gün ${fmt(asset.unit_start)} ederdi; TÜFE'ye göre güncellenen ${tlFormatter.format(ctx.result)} bugün ${fmt(asset.unit_end)} eder.`
    : `${tlFormatter.format(ctx.amount)} o gün ${fmt(asset.unit_start)} ${asset.label.toLowerCase()} alırdı; TÜFE'ye göre güncellenen ${tlFormatter.format(ctx.result)} bugün ${fmt(asset.unit_end)} alır.`;

  const verdict = isCurrency
    ? (pos
      ? `Resmi enflasyon ${asset.label} karşısında öne geçti — paranızın ${asset.label} cinsinden alım gücü ${pctAbs} <b>arttı</b>.`
      : `${asset.label} resmi enflasyonu geçti — paranızın ${asset.label} cinsinden alım gücü ${pctAbs} <b>eridi</b>.`)
    : (pos
      ? `${asset.label} resmi enflasyonun gerisinde kaldı — aynı parayla ${pctAbs} <b>daha çok</b> alıyorsunuz.`
      : `${asset.label} resmi enflasyonu geçti — aynı parayla ${pctAbs} <b>daha az</b> alıyorsunuz.`);

  return popBody(`${asset.label} nasıl hesaplandı?`, rows, noteHTML, calcLine, verdict, pos);
}

// Asgari ücret açılır kutusunun içeriği.
function minwagePopHTML(m, ctx) {
  const rise = (m.wage_end / m.wage_start - 1) * 100;
  const riseAbs = fmtChange(Math.abs(rise));
  const riseVerb = rise >= 0 ? 'arttı' : 'azaldı';
  const pos = m.change_pct >= 0;
  const pctAbs = fmtChange(Math.abs(m.change_pct));

  const rows =
    `<div class="chip-pop-row"><span>${ctx.startYear} net asgari ücret</span><span>${tlFormatter.format(m.wage_start)}</span></div>` +
    `<div class="chip-pop-row"><span>${ctx.endYear} net asgari ücret</span><span>${tlFormatter.format(m.wage_end)}</span></div>`;
  const riseLine = `Asgari ücret bu dönemde ${riseAbs} ${riseVerb}.`;
  const calcLine = `${tlFormatter.format(ctx.amount)}, ${ctx.startYear} yılında ${numFormatter.format(m.ratio_start)} maaş ederdi; TÜFE'ye göre güncellenen ${tlFormatter.format(ctx.result)}, ${ctx.endYear} yılında ${numFormatter.format(m.ratio_end)} maaş eder.`;
  const verdict = pos
    ? `Tutarınız daha çok “maaş” ediyor — alım gücünüz asgari ücrete göre ${pctAbs} <b>arttı</b>.`
    : `Asgari ücret paranızdan hızlı arttı — tutarınız ${pctAbs} <b>daha az “maaş”</b> ediyor.`;

  return popBody('Asgari ücret nasıl hesaplandı?', rows, riseLine, calcLine, verdict, pos);
}

// Açık tüm bilgi kutularını kapatır.
function closeAllChipPops() {
  document.querySelectorAll('.chip-pop:not(.hidden)').forEach((p) => p.classList.add('hidden'));
  document.querySelectorAll('.chip--open').forEach((c) => c.classList.remove('chip--open'));
  document.querySelectorAll('.chip-info[aria-expanded="true"]').forEach((b) => b.setAttribute('aria-expanded', 'false'));
}

// Bir bilgi kutusunu açar ve yatayda görüntü alanı (viewport) içinde kalacak şekilde konumlar.
function openChipPop(chip, btn) {
  const pop = chip.querySelector('.chip-pop');
  if (!pop) return;
  pop.classList.remove('hidden');
  chip.classList.add('chip--open');
  btn.setAttribute('aria-expanded', 'true');

  // Önce sol kenardan ölç, sonra ekranı taşmayacak şekilde sola/sağa kaydır.
  pop.style.left = '0px';
  pop.style.right = 'auto';
  const w = pop.offsetWidth;
  const chipRect = chip.getBoundingClientRect();
  const vw = document.documentElement.clientWidth;
  const margin = 8;
  let leftVP = chipRect.right - w; // varsayılan: kutunun sağ kenarı chip'in sağına hizalı
  leftVP = Math.max(margin, Math.min(leftVP, vw - w - margin));
  pop.style.left = (leftVP - chipRect.left) + 'px';
}

// Değerleri 0–1 aralığına eşleyen ölçek. Çok uzun dönemlerde (ör. 1964→2026, değer
// 37 milyon kat artar) doğrusal eksen düz çizgi gibi görünür; bu yüzden aradaki fark
// 100 katı aşınca logaritmik eksene geçilir — enflasyon grafiklerinde standart yaklaşım.
function chartScale(vals) {
  const max = Math.max(...vals), min = Math.min(...vals);
  if (min > 0 && max / min > 100) {
    const lo = Math.log10(min), hi = Math.log10(max);
    const fn = (v) => (Math.log10(Math.max(v, min)) - lo) / ((hi - lo) || 1);
    fn.log = true;
    return fn;
  }
  return (v) => (v - min) / ((max - min) || 1);
}

function drawChart(series) {
  const c = el('chart');
  if (!series || !series.labels || series.labels.length === 0) { c.innerHTML = ''; return; }
  const lines = { tufe: series.tufe, enag: series.enag, ito: series.ito };
  const vals = [];
  for (const k in lines) if (lines[k]) lines[k].forEach((x) => { if (x != null) vals.push(x); });
  if (vals.length === 0) { c.innerHTML = ''; return; }

  const SC = seriesColors();
  const scale = chartScale(vals);
  el('chartScaleNote').classList.toggle('hidden', !scale.log);
  const W = 600, H = 140, padT = 6, padB = 6, padX = 2, n = series.labels.length;
  const X = (i) => padX + (W - 2 * padX) * (n <= 1 ? 0.5 : i / (n - 1));
  const Y = (val) => padT + (H - padT - padB) * (1 - scale(val));
  const dpath = (arr) => {
    let d = '', started = false;
    arr.forEach((val, i) => {
      if (val == null) { started = false; return; }
      d += (started ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(val).toFixed(1) + ' ';
      started = true;
    });
    return d.trim();
  };

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="140" preserveAspectRatio="none" style="display:block">`;
  const area = dpath(lines.tufe);
  if (area) {
    svg += `<path d="${area} L${X(n - 1).toFixed(1)},${H - padB} L${X(0).toFixed(1)},${H - padB} Z" fill="${SC.tufe}" opacity="0.05"/>`;
  }
  for (const k of ['ito', 'enag', 'tufe']) {
    if (!lines[k]) continue;
    svg += `<path d="${dpath(lines[k])}" fill="none" stroke="${SC[k]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`;
  }
  svg += '</svg>';
  c.innerHTML = svg;
}

// ---------- Dışa aktarma (paylaş / görseli indir) ----------

// Sonuç kartını markaya özel sabit boyutlu bir görsele (PNG) çizer.
// Bağımlılıksız: yalnızca Canvas API. Fontlar yüklendikten sonra çağrılmalı.
async function buildShareCanvas(theme = 'light') {
  if (!lastResult) return null;
  const { payload, data } = lastResult;
  try { await document.fonts.ready; } catch (_) { /* yoksay */ }

  const W = 1080, H = 1350, P = 76;
  const C = SHARE_PALETTES[theme] || SHARE_PALETTES.light;
  const canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');
  ctx.textBaseline = 'alphabetic';

  // Zemin
  ctx.fillStyle = C.paper;
  ctx.fillRect(0, 0, W, H);

  const serif = (s, w = 600) => `${w} ${s}px 'Fraunces', Georgia, serif`;
  const sans = (s, w = 400) => `${w} ${s}px 'Inter', system-ui, sans-serif`;
  let y = P + 30;

  // Üst etiket
  ctx.fillStyle = C.accent;
  ctx.font = sans(22, 700);
  ctx.fillText('TÜRKİYE · ENFLASYON', P, y);

  // Tarih aralığı
  y += 56;
  ctx.fillStyle = C.ink;
  ctx.font = sans(34, 700);
  ctx.fillText((el('resultRange').textContent || '').toLocaleUpperCase('tr-TR'), P, y);

  // Etiket
  y += 60;
  ctx.fillStyle = C.soft;
  ctx.font = sans(24, 500);
  ctx.fillText('Resmi (TÜFE) karşılığı', P, y);

  // Başlangıç tutarı → sonuç ("₺1.000 → ₺32.176") — girilen tutar net görünsün.
  const fromStr = tlFormatter.format(payload.amount);
  const valStr = tlFormatter.format(data.result);
  const FROM_SIZE = 50, ARROW_SIZE = 40, GAP = 20;
  ctx.font = serif(FROM_SIZE, 600);
  const fromW = ctx.measureText(fromStr).width;
  ctx.font = sans(ARROW_SIZE, 700);
  const arrowW = ctx.measureText('→').width;
  // Sonuç yazı boyutunu, "from → to" tek satıra sığacak kadar küçült (taşma olmasın).
  let resSize = 84;
  let valW = 0;
  while (resSize > 44) {
    ctx.font = serif(resSize, 600);
    valW = ctx.measureText(valStr).width;
    if (fromW + GAP + arrowW + GAP + valW <= W - 2 * P) break;
    resSize -= 4;
  }

  y += 86;
  let cx = P;
  ctx.fillStyle = C.soft;
  ctx.font = serif(FROM_SIZE, 600);
  ctx.fillText(fromStr, cx, y);
  cx += fromW + GAP;
  ctx.font = sans(ARROW_SIZE, 700);
  ctx.fillText('→', cx, y);
  cx += arrowW + GAP;
  ctx.fillStyle = C.ink;
  ctx.font = serif(resSize, 600);
  ctx.fillText(valStr, cx, y);
  cx += valW;

  // Yüzde değişim — sığarsa sonucun yanına, sığmazsa alt satıra.
  const up = data.change_pct >= 0;
  const chgStr = `${up ? '▲' : '▼'} %${numFormatter.format(Math.abs(data.change_pct))}`;
  ctx.fillStyle = up ? C.accent : C.up;
  ctx.font = sans(38, 700);
  const chgW = ctx.measureText(chgStr).width;
  if (cx + 26 + chgW <= W - P) {
    ctx.fillText(chgStr, cx + 26, y);
  } else {
    y += 50; ctx.fillText(chgStr, P, y);
  }

  // Çarpan + endeks
  y += 44;
  ctx.fillStyle = C.soft;
  ctx.font = sans(22, 500);
  ctx.fillText(
    `Çarpan ${numFormatter.format(data.multiplier)}×  ·  endeks ${numFormatter.format(data.start_index)} → ${numFormatter.format(data.end_index)}`,
    P, y,
  );

  // Grafik
  y += 40;
  const series = data.series || {};
  const lines = { tufe: series.tufe, enag: series.enag, ito: series.ito };
  const vals = [];
  for (const k in lines) if (lines[k]) lines[k].forEach((x) => { if (x != null) vals.push(x); });
  const lastVal = (arr) => { if (!arr) return null; for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return arr[i]; return null; };

  if (vals.length) {
    // Lejant
    const legend = [];
    if (lastVal(lines.tufe) != null) legend.push(['TÜFE', C.tufe, lastVal(lines.tufe)]);
    if (lastVal(lines.enag) != null) legend.push(['ENAG*', C.enag, lastVal(lines.enag)]);
    if (lastVal(lines.ito) != null) legend.push(['İTO*', C.ito, lastVal(lines.ito)]);
    let lx = P;
    ctx.font = sans(20, 600);
    for (const [label, color, val] of legend) {
      ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(lx + 7, y - 6, 7, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = C.ink;
      const txt = `${label} ${tlFormatter.format(val)}`;
      ctx.fillText(txt, lx + 22, y);
      lx += 22 + ctx.measureText(txt).width + 34;
    }

    const cx0 = P, cw = W - 2 * P, cy0 = y + 24, ch = 300;
    const scale = chartScale(vals);
    const n = series.labels.length;
    const X = (i) => cx0 + cw * (n <= 1 ? 0.5 : i / (n - 1));
    const Y = (v) => cy0 + ch * (1 - scale(v));
    const trace = (arr) => {
      ctx.beginPath();
      let started = false;
      arr.forEach((v, i) => {
        if (v == null) { started = false; return; }
        if (started) ctx.lineTo(X(i), Y(v)); else ctx.moveTo(X(i), Y(v));
        started = true;
      });
    };
    // TÜFE alan dolgusu
    if (lines.tufe) {
      trace(lines.tufe);
      ctx.lineTo(X(n - 1), cy0 + ch); ctx.lineTo(X(0), cy0 + ch); ctx.closePath();
      ctx.fillStyle = C.ink; ctx.globalAlpha = 0.05; ctx.fill(); ctx.globalAlpha = 1;
    }
    ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.lineWidth = 3;
    for (const k of ['ito', 'enag', 'tufe']) {
      if (!lines[k]) continue;
      trace(lines[k]); ctx.strokeStyle = C[k]; ctx.stroke();
    }
    // Eksen etiketleri
    ctx.fillStyle = C.soft; ctx.font = sans(18, 500);
    ctx.fillText(monthShort(data.start_key), cx0, cy0 + ch + 28);
    const endLbl = monthShort(data.end_key);
    ctx.fillText(endLbl, cx0 + cw - ctx.measureText(endLbl).width, cy0 + ch + 28);
    y = cy0 + ch + 28;
  }

  // Varlık / asgari ücret özetleri (2 sütun)
  y += 52;
  const rows = [];
  const a = data.assets || {};
  if (data.minwage) {
    rows.push(['Asgari ücret', `${numFormatter.format(data.minwage.ratio_start)} → ${numFormatter.format(data.minwage.ratio_end)} maaş`, data.minwage.change_pct]);
  }
  // Görsel sabit boyutlu; en fazla 6 kutu (3 satır) sığar.
  for (const key of ['usd', 'eur', 'gold', 'cgold', 'bist', 'brent']) {
    if (rows.length >= 6) break;
    const as = a[key];
    if (!as) continue;
    const fmt = unitFormatter(as);
    rows.push([as.label, `${fmt(as.unit_start)} → ${fmt(as.unit_end)}`, as.change_pct]);
  }
  const colW = (W - 2 * P - 28) / 2;
  rows.forEach((r, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const bx = P + col * (colW + 28);
    const by = y + row * 92;
    ctx.strokeStyle = C.line; ctx.lineWidth = 1.5;
    roundRect(ctx, bx, by, colW, 76, 12); ctx.stroke();
    ctx.fillStyle = C.ink; ctx.font = sans(20, 600);
    ctx.fillText(r[0], bx + 18, by + 30);
    const pos = r[2] >= 0;
    const pct = fmtChangeSigned(r[2]);
    ctx.fillStyle = pos ? C.up : C.accent; ctx.font = sans(20, 700);
    ctx.fillText(pct, bx + colW - 18 - ctx.measureText(pct).width, by + 30);
    ctx.fillStyle = C.soft; ctx.font = sans(20, 500);
    ctx.fillText(r[1], bx + 18, by + 58);
  });
  y += Math.ceil(rows.length / 2) * 92;

  // Alt bilgi — kişisel ad / site adresi YOK; yalnızca ürün adı + bağımsızlık dipnotu.
  ctx.strokeStyle = C.line; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(P, H - 120); ctx.lineTo(W - P, H - 120); ctx.stroke();
  ctx.fillStyle = C.ink; ctx.font = sans(24, 700);
  ctx.fillText('TL Enflasyon Hesaplayıcı', P, H - 80);
  ctx.fillStyle = C.soft; ctx.font = sans(18, 400);
  ctx.fillText('Kaynak: TCMB EVDS. ENAG ve İTO resmi Türkiye enflasyonu değildir.', P, H - 44);

  return canvas;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function canvasToBlob(canvas) {
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
}

async function downloadShareImage(theme = shareTheme) {
  const canvas = await buildShareCanvas(theme);
  if (!canvas) return;
  const blob = await canvasToBlob(canvas);
  if (!blob) { showAlert('Görsel oluşturulamadı.', 'error'); return; }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'tl-enflasyon.png';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function shareShareImage(theme = shareTheme) {
  const canvas = await buildShareCanvas(theme);
  if (!canvas) return;
  const blob = await canvasToBlob(canvas);
  const title = 'TL Enflasyon Hesaplayıcı';
  const text = `${el('resultRange').textContent} · ${tlFormatter.format(lastResult.data.result)}`;
  const file = blob ? new File([blob], 'tl-enflasyon.png', { type: 'image/png' }) : null;

  // 1) Dosya paylaşımı (mobil/destekleyen tarayıcılar)
  if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
    try { await navigator.share({ files: [file], title, text }); return; }
    catch (err) { if (err && err.name === 'AbortError') return; }
  }
  // 2) URL/metin paylaşımı
  if (navigator.share) {
    try { await navigator.share({ title, text, url: location.href }); return; }
    catch (err) { if (err && err.name === 'AbortError') return; }
  }
  // 3) Son çare: görseli indir + bilgilendir
  await downloadShareImage();
  showAlert('Paylaşım bu cihazda desteklenmiyor; görsel indirildi.', 'warning');
}

// Düğmeye kısa süreli geri bildirim yazısı/işareti gösterir, sonra eski haline döner.
// (Uyarı kutusu modalın arkasında kaldığı için kopyalama sonucu burada gösterilir.)
function flashButton(btn, message, ok = true) {
  if (btn._flashTimer) { clearTimeout(btn._flashTimer); btn.innerHTML = btn._flashOriginal; }
  btn._flashOriginal = btn.innerHTML;
  const icon = ok
    ? `<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />`
    : `<circle cx="12" cy="12" r="9" /><path stroke-linecap="round" d="M12 8v5M12 16h.01" />`;
  btn.innerHTML =
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4">${icon}</svg> ${message}`;
  btn._flashTimer = setTimeout(() => {
    btn.innerHTML = btn._flashOriginal;
    btn._flashTimer = null;
  }, 1700);
}

// Görseli panoya (clipboard) PNG olarak kopyalar. Desteklenmeyen tarayıcılarda indirmeye düşer.
async function copyShareImage(theme = shareTheme) {
  const btn = el('copyBtn');
  const canvas = await buildShareCanvas(theme);
  if (!canvas) return;
  const blob = await canvasToBlob(canvas);
  if (!blob) { flashButton(btn, 'Oluşturulamadı', false); return; }
  try {
    if (!(navigator.clipboard && window.ClipboardItem)) throw new Error('clipboard yok');
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
    flashButton(btn, 'Kopyalandı');
  } catch (err) {
    // Pano API'si yoksa/engellendiyse görseli indir ve kullanıcıyı bilgilendir.
    await downloadShareImage(theme);
    flashButton(btn, 'İndirildi', false);
  }
}

// ---------- Paylaşım önizleme modalı ----------

// Seçili temayla görseli çizip <img> önizlemesine ve segment düğmelerine yansıtır.
async function renderSharePreview() {
  const canvas = await buildShareCanvas(shareTheme);
  if (!canvas) return;
  el('sharePreview').src = canvas.toDataURL('image/png');
  document.querySelectorAll('[data-share-theme]').forEach((b) =>
    b.classList.toggle('active', b.dataset.shareTheme === shareTheme));
}

function openShareModal() {
  if (!lastResult) return;
  shareTheme = (window.TLTheme && window.TLTheme.current()) || 'light';
  el('shareModal').classList.remove('hidden');
  exportBtn.setAttribute('aria-expanded', 'true');
  renderSharePreview();
}

function closeShareModal() {
  el('shareModal').classList.add('hidden');
  exportBtn.setAttribute('aria-expanded', 'false');
}

// ---------- Güncel enflasyon şeridi ----------

// En son açıklanan aya ait ölçümler (TÜFE, ENAG, İTO, ÜFE, konut) ve varlık fiyatları.
// Resmi olmayan ölçümler küçük bir noktayla işaretlenir.
function renderLatestStrip(latest) {
  if (!latest) return;
  const cards = [];

  for (const m of latest.measures || []) {
    if (m.annual == null) continue;
    const dot = m.official ? '' : '<span class="stat-dot" aria-hidden="true"></span>';
    const monthly = m.monthly == null ? '' : ` · aylık %${numFormatter.format(m.monthly)}`;
    cards.push(
      `<div class="stat" title="${m.hint || ''}">
         <div class="stat-label">${dot}${m.label}</div>
         <div class="stat-value">${fmtChange(m.annual)}</div>
         <div class="stat-sub">${monthShort(m.month)}${monthly}</div>
       </div>`);
  }

  for (const a of latest.assets || []) {
    const annual = a.annual == null ? '' : ` · yıllık ${fmtChangeSigned(a.annual)}`;
    cards.push(
      `<div class="stat">
         <div class="stat-label">${a.label}</div>
         <div class="stat-value">${tlFormatter.format(a.price)}</div>
         <div class="stat-sub">${monthShort(a.month)}${annual}</div>
       </div>`);
  }

  el('latestStrip').innerHTML = cards.join('');
}

// ---------- Yıllara göre enflasyon tablosu ----------

function renderYearly(rows) {
  const cell = (v) => (v == null ? '<td class="muted">—</td>' : `<td>${fmtChange(v)}</td>`);
  el('yearlyBody').innerHTML = (rows || []).slice().reverse().map((r) => {
    const partial = r.partial && r.through
      ? ` <span class="muted">· ${monthShort(r.through)}</span>` : '';
    return `<tr><td>${r.year}${partial}</td>${cell(r.tufe)}${cell(r.enag)}${cell(r.ito)}</tr>`;
  }).join('');
}

function openYearlyModal() { el('yearlyModal').classList.remove('hidden'); }
function closeYearlyModal() { el('yearlyModal').classList.add('hidden'); }

// ---------- Başlatma ----------

async function init() {
  try {
    const resp = await fetch('/api/data');
    const data = await resp.json();
    if (!resp.ok) {
      showAlert(data.detail || 'Veri yüklenemedi.', 'error');
      return;
    }
    DATA.values = data.values || {};
    buildSelectors();
    renderLatestStrip(data.latest);
    renderYearly(data.yearly);
    if (data.start && data.end) {
      el('rangeHint').textContent = `${data.start.slice(0, 4)}'ten bugüne`;
    }
    if (data.fetched_at) {
      const d = new Date(data.fetched_at * 1000);
      el('footerMeta').textContent = ` Güncel: ${d.toLocaleDateString('tr-TR')}.`;
    }
  } catch (err) {
    showAlert('Veri sunucusuna ulaşılamadı. Backend çalışıyor mu?', 'error');
  }
}

calcBtn.addEventListener('click', calculate);
startYear.addEventListener('change', () => {
  refreshMonths(startMonth, startYear.value, 'first');
  updateAmountHint();
});
endYear.addEventListener('change', () => refreshMonths(endMonth, endYear.value, 'last'));
amountInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') calculate(); });
amountInput.addEventListener('blur', () => {
  const n = parseAmount(amountInput.value);
  if (n && n > 0) amountInput.value = numFormatter.format(n);
});

// "Diğer varlıklar ve göstergeler" bölümünü aç/kapat
el('moreToggle').addEventListener('click', () =>
  setMoreOpen(el('moreToggle').getAttribute('aria-expanded') !== 'true'));

// Yıllara göre enflasyon tablosu
el('yearlyBtn').addEventListener('click', openYearlyModal);
el('yearlyClose').addEventListener('click', closeYearlyModal);
el('yearlyModal').addEventListener('click', (e) => {
  if (e.target === el('yearlyModal')) closeYearlyModal();
});

// Dışa aktarma: önizleme modalı (görsel açık/karanlık seçilebilir, indirmeden önce görülür)
exportBtn.addEventListener('click', openShareModal);
el('shareClose').addEventListener('click', closeShareModal);
el('shareModal').addEventListener('click', (e) => { if (e.target === el('shareModal')) closeShareModal(); });
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (!el('shareModal').classList.contains('hidden')) closeShareModal();
  if (!el('yearlyModal').classList.contains('hidden')) closeYearlyModal();
});
document.querySelectorAll('[data-share-theme]').forEach((b) =>
  b.addEventListener('click', () => { shareTheme = b.dataset.shareTheme; renderSharePreview(); }));
el('shareBtn').addEventListener('click', () => shareShareImage(shareTheme));
el('copyBtn').addEventListener('click', () => copyShareImage(shareTheme));
el('downloadBtn').addEventListener('click', () => downloadShareImage(shareTheme));

// Chip "nasıl hesaplandı?" bilgi kutuları — delegation (chip'ler her hesapla'da yeniden üretilir).
// "i" düğmesine basınca aç/kapat; başka yere ya da kutu dışına tıklayınca / Escape ile kapat.
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.chip-info');
  if (btn) {
    const chip = btn.closest('.chip');
    const isOpen = !chip.querySelector('.chip-pop').classList.contains('hidden');
    closeAllChipPops();
    if (!isOpen) openChipPop(chip, btn);
    return;
  }
  if (e.target.closest('.chip-pop')) return; // kutu içine tıklama kapatmasın
  closeAllChipPops();
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeAllChipPops(); });

// Site teması değişince (düğme ya da sistem) açıktaki sonucun grafiğini yeniden renklendir.
const _themeObserver = new MutationObserver(() => {
  if (lastResult) { renderChartLegend(lastResult.data); drawChart(lastResult.data.series); }
});
_themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

init();
