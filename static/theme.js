// Açık/karanlık tema yöneticisi — tüm sayfalarda <head> içinde, render öncesi yüklenir.
// Varsayılan: sistem ayarını izle (prefers-color-scheme). Kullanıcı düğmeyle değiştirirse
// seçim localStorage'da saklanır ve sonraki ziyaretlerde uygulanır.
(function () {
  var STORAGE_KEY = 'tl-tema';

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // Geçerli seçim: kayıtlı tercih varsa onu, yoksa sistem tercihini döndürür.
  function resolveTheme() {
    var saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { /* özel mod vb. */ }
    if (saved === 'light' || saved === 'dark') return saved;
    return systemPrefersDark() ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }

  // 1) Flash olmaması için temayı hemen (body çizilmeden) uygula.
  applyTheme(resolveTheme());

  // 2) Düğmeleri bağla ve sistem değişimini (kayıtlı tercih yoksa) izle.
  function wire() {
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var next = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* yoksay */ }
        applyTheme(next);
      });
    });
  }

  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      var saved = null;
      try { saved = localStorage.getItem(STORAGE_KEY); } catch (err) { /* yoksay */ }
      if (saved !== 'light' && saved !== 'dark') applyTheme(e.matches ? 'dark' : 'light');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }

  // Diğer scriptlerin mevcut temayı okuyabilmesi için küçük yardımcı.
  window.TLTheme = {
    current: function () { return document.documentElement.classList.contains('dark') ? 'dark' : 'light'; },
  };
})();
