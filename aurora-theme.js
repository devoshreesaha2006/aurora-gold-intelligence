/* Shared appearance control for authenticated AURORA research pages.
 * Enforces Dark / Gold Midnight Theme permanently. Light mode is removed across the entire project.
 */
(() => {
  const STORAGE_KEY = 'aurora-main-theme';
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.setItem(STORAGE_KEY, 'dark');
  } catch (_) {}

  const enforceDark = () => {
    document.body.dataset.auroraTheme = 'dark';
    document.documentElement.style.colorScheme = 'dark';
    const button = document.getElementById('auroraThemeToggle');
    if (button) button.remove();
    document.querySelectorAll('.aurora-theme-toggle').forEach(el => el.remove());
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enforceDark);
  } else {
    enforceDark();
  }
})();
