(function () {
  const root = document.documentElement;
  const stored = localStorage.getItem('color-scheme');
  if (stored === 'dark') root.setAttribute('data-color-scheme', 'dark');

  window.toggleTheme = function () {
    const isDark = root.getAttribute('data-color-scheme') === 'dark';
    if (isDark) {
      root.removeAttribute('data-color-scheme');
      localStorage.setItem('color-scheme', 'light');
    } else {
      root.setAttribute('data-color-scheme', 'dark');
      localStorage.setItem('color-scheme', 'dark');
    }
  };
})();
