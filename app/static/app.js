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

  window.toggleMobileNav = function () {
    const el = document.getElementById('mobileNav');
    if (!el) return;

    if (window.matchMedia('(min-width: 768px)').matches) {
      const btns = document.querySelectorAll('button[aria-controls="mobileNav"]');
      btns.forEach((btn) => btn.setAttribute('aria-expanded', 'false'));
      document.body.classList.remove('overflow-hidden');
      el.classList.add('hidden');
      return;
    }

    const willOpen = el.classList.contains('hidden');
    el.classList.toggle('hidden');

    const btns = document.querySelectorAll('button[aria-controls="mobileNav"]');
    btns.forEach((btn) => btn.setAttribute('aria-expanded', willOpen ? 'true' : 'false'));

    document.body.classList.toggle('overflow-hidden', willOpen);
  };

  window.togglePortalNav = function () {
    if (window.matchMedia('(min-width: 768px)').matches) {
      const collapsed = document.documentElement.classList.toggle('sidebar-collapsed');
      const btns = document.querySelectorAll('button[aria-controls="mobileNav"]');
      btns.forEach((btn) => btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true'));
      return;
    }

    window.toggleMobileNav();
  };

  window.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    const el = document.getElementById('mobileNav');
    if (!el) return;
    if (!el.classList.contains('hidden')) window.toggleMobileNav();
  });
})();
