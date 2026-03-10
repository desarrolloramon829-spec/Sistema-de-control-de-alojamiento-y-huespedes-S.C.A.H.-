/**
 * S.C.A.H. Web - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
  document.body.classList.add('is-loaded');

  document.querySelectorAll('.fade-up').forEach(function (element, index) {
    const delay = Math.min(index * 45, 320);
    element.style.transitionDelay = `${delay}ms`;
  });

  // ===== Auto-dismiss flash alerts =====
  document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // ===== Active sidebar link =====
  const currentPath = window.location.pathname;
  document
    .querySelectorAll('.sidebar-nav .nav-link, .offcanvas .nav-link')
    .forEach(function (link) {
      const href = link.getAttribute('href');
      if (href && currentPath.startsWith(href) && href !== '/') {
        link.classList.add('active');
      } else if (href === '/' && currentPath === '/dashboard') {
        link.classList.add('active');
      }
    });

  document.querySelectorAll('[data-countup]').forEach(function (el) {
    const target = Number(el.dataset.countup || '0');
    const duration = 700;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const current = Math.round(target * progress);
      el.textContent = current.toLocaleString('es-AR');
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  });

  // ===== Close offcanvas on link click (mobile) =====
  const offcanvasEl = document.getElementById('sidebarMenu');
  if (offcanvasEl) {
    offcanvasEl.querySelectorAll('.nav-link').forEach(function (link) {
      link.addEventListener('click', function () {
        const offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
        if (offcanvas) offcanvas.hide();
      });
    });
  }

  // ===== Confirm delete actions =====
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm(form.dataset.confirm)) {
        e.preventDefault();
      }
    });
  });

  // ===== Tooltips (Bootstrap) =====
  const tooltipTriggerList = document.querySelectorAll(
    '[data-bs-toggle="tooltip"]'
  );
  tooltipTriggerList.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  document
    .querySelectorAll('.btn, .quick-action-tile, .sidebar-nav .nav-link')
    .forEach(function (element) {
      element.addEventListener('pointerdown', function () {
        element.classList.add('is-pressed');
      });

      ['pointerup', 'pointerleave', 'pointercancel'].forEach(function (event) {
        element.addEventListener(event, function () {
          element.classList.remove('is-pressed');
        });
      });
    });

  // ===== PWA install prompt =====
  let deferredPrompt;
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;

    // Show install button if exists
    const installBtn = document.getElementById('installPwa');
    if (installBtn) {
      installBtn.style.display = 'inline-block';
      installBtn.addEventListener('click', function () {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function () {
          deferredPrompt = null;
          installBtn.style.display = 'none';
        });
      });
    }
  });

  // ===== Register service worker =====
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function () {
      // SW registration failed, ignore
    });
  }
});
