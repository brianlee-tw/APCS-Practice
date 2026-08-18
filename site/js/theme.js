const THEME_KEY = 'apcs_theme_preference';

export function preferredTheme(storage = window.localStorage, media = window.matchMedia('(prefers-color-scheme: dark)')) {
  const saved = storage.getItem(THEME_KEY);
  if (saved === 'light' || saved === 'dark') return saved;
  return media.matches ? 'dark' : 'light';
}

export function applyTheme(theme, { persist = true } = {}) {
  const normalized = theme === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = normalized;
  document.documentElement.style.colorScheme = normalized;
  if (persist) localStorage.setItem(THEME_KEY, normalized);

  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.content = normalized === 'dark' ? '#0b0d12' : '#f6f7f9';

  for (const toggle of document.querySelectorAll('[data-theme-toggle]')) {
    const next = normalized === 'dark' ? 'light' : 'dark';
    toggle.dataset.theme = normalized;
    toggle.setAttribute('aria-label', `切換為${next === 'dark' ? '深色' : '淺色'}模式`);
    toggle.setAttribute('title', `切換為${next === 'dark' ? '深色' : '淺色'}模式`);
    const icon = toggle.querySelector('[data-theme-icon]');
    if (icon) icon.textContent = normalized === 'dark' ? '☾' : '☀';
    const label = toggle.querySelector('[data-theme-label]');
    if (label) label.textContent = normalized === 'dark' ? '深色' : '淺色';
  }
}

export function initTheme() {
  applyTheme(preferredTheme(), { persist: false });
  for (const toggle of document.querySelectorAll('[data-theme-toggle]')) {
    if (toggle.dataset.bound === 'true') continue;
    toggle.dataset.bound = 'true';
    toggle.addEventListener('click', () => {
      const current = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initTheme, { once: true });
else initTheme();
