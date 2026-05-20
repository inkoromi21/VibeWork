/** Переключатель темы для отдельных страниц (регистрация и т.д.). На главной — дублируется в script.js. */
(function () {
  const THEME_STORAGE_KEY = "vibework_theme";

  function syncThemeToggleButton(isDark) {
    document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
      btn.setAttribute("aria-pressed", isDark ? "true" : "false");
      btn.title = isDark ? "Светлая тема" : "Тёмная тема";
      btn.setAttribute("aria-label", isDark ? "Включить светлую тему" : "Включить тёмную тему");
      btn.textContent = isDark ? "☀️" : "🌙";
    });
  }

  function applyTheme(mode) {
    const root = document.documentElement;
    if (mode === "dark") root.setAttribute("data-theme", "dark");
    else root.removeAttribute("data-theme");
    try {
      localStorage.setItem(THEME_STORAGE_KEY, mode === "dark" ? "dark" : "light");
    } catch (_) {}
    syncThemeToggleButton(mode === "dark");
  }

  function initThemeToggle() {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === "dark") document.documentElement.setAttribute("data-theme", "dark");
      else if (stored === "light") document.documentElement.removeAttribute("data-theme");
    } catch (_) {}
    syncThemeToggleButton(document.documentElement.getAttribute("data-theme") === "dark");
    document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
      if (btn.dataset.themeBound) return;
      btn.dataset.themeBound = "1";
      btn.addEventListener("click", () => {
        const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(next);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initThemeToggle);
  } else {
    initThemeToggle();
  }
})();
