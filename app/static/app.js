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

  function initLandingEnhancements() {
    const isLanding = document.getElementById('top');
    if (!isLanding) return;

    document.querySelectorAll('a[href^="#"]').forEach((a) => {
      a.addEventListener('click', (e) => {
        const href = a.getAttribute('href') || '';
        if (href.length < 2) return;
        const target = document.querySelector(href);
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        history.replaceState(null, '', href);
      });
    });

    const revealEls = Array.from(document.querySelectorAll('.landing-reveal'));
    if (revealEls.length) {
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          });
        },
        { root: null, threshold: 0.12 }
      );
      revealEls.forEach((el) => io.observe(el));
      revealEls.slice(0, 6).forEach((el) => el.classList.add('is-visible'));
    }

    const form = document.getElementById('contactForm');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();

        const data = new FormData(form);
        const name = (data.get('name') || '').toString().trim();
        const email = (data.get('email') || '').toString().trim();
        const topic = (data.get('topic') || '').toString().trim();
        const message = (data.get('message') || '').toString().trim();

        const subject = encodeURIComponent(`[MedicareX] ${topic} — ${name}`);
        const body = encodeURIComponent(`Name: ${name}\nEmail: ${email}\nTopic: ${topic}\n\n${message}`);
        const to = '';

        window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLandingEnhancements);
  } else {
    initLandingEnhancements();
  }
})();
