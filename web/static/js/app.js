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
  const installButtons = document.querySelectorAll('[data-install-pwa]');

  installButtons.forEach(function (button) {
    button.style.display = 'none';
  });

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;

    // Show install button if exists
    installButtons.forEach(function (button) {
      button.style.display = 'inline-block';
      button.onclick = function () {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function () {
          deferredPrompt = null;
          installButtons.forEach(function (item) {
            item.style.display = 'none';
          });
        });
      };
    });
  });

  window.addEventListener('appinstalled', function () {
    installButtons.forEach(function (button) {
      button.style.display = 'none';
    });
  });

  // ===== Register service worker =====
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function () {
      // SW registration failed, ignore
    });
  }

  const connectivityTargets = document.querySelectorAll('[data-online-status]');
  const offlineBanner = document.querySelector('[data-offline-banner]');
  const onlineRequiredForms = document.querySelectorAll(
    'form[data-requires-online]'
  );
  const alertBadges = document.querySelectorAll('[data-alert-count-badge]');
  const enableNotificationsButton = document.querySelector(
    '[data-enable-alert-notifications]'
  );
  let lastAlertCount = null;

  function updateConnectivityState() {
    const online = navigator.onLine;

    connectivityTargets.forEach(function (target) {
      target.textContent = online ? 'En línea' : 'Sin conexión';
    });

    if (offlineBanner) {
      offlineBanner.classList.toggle('d-none', online);
    }

    document.body.classList.toggle('is-offline', !online);

    onlineRequiredForms.forEach(function (form) {
      form
        .querySelectorAll('button[type="submit"], input[type="submit"]')
        .forEach(function (button) {
          button.disabled = !online;
        });

      form.querySelectorAll('[data-offline-note]').forEach(function (note) {
        note.classList.toggle('d-none', online);
      });
    });
  }

  window.addEventListener('online', updateConnectivityState);
  window.addEventListener('offline', updateConnectivityState);
  updateConnectivityState();

  function updateAlertBadges(count) {
    alertBadges.forEach(function (badge) {
      badge.textContent = String(count);
      badge.classList.toggle('d-none', count <= 0);
    });
  }

  function showAlertNotification(count) {
    if (!('Notification' in window) || Notification.permission !== 'granted') {
      return;
    }

    const title = 'S.C.A.H. - Alertas operativas';
    const body =
      count === 1
        ? 'Hay 1 alerta pendiente de revisión.'
        : `Hay ${count} alertas pendientes de revisión.`;

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready
        .then(function (registration) {
          if (registration && registration.showNotification) {
            return registration.showNotification(title, {
              body: body,
              tag: 'scah-alertas',
              icon: '/static/img/icon-app.svg',
              badge: '/static/img/icon-app.svg',
              data: { url: '/alertas/' },
            });
          }
          return new Notification(title, { body: body });
        })
        .catch(function () {
          new Notification(title, { body: body });
        });
      return;
    }

    new Notification(title, { body: body });
  }

  function pollAlerts() {
    fetch('/alertas/api/count', {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error('No se pudo consultar alertas');
        }
        return response.json();
      })
      .then(function (data) {
        const count = Number(data.pending_count || 0);
        updateAlertBadges(count);
        if (lastAlertCount !== null && count > lastAlertCount) {
          showAlertNotification(count);
        }
        lastAlertCount = count;
      })
      .catch(function () {
        // Ignore alert polling errors silently
      });
  }

  if (alertBadges.length) {
    pollAlerts();
    const seconds = Number(document.body.dataset.alertPollSeconds || '60');
    window.setInterval(pollAlerts, Math.max(seconds, 20) * 1000);
  }

  if (enableNotificationsButton && 'Notification' in window) {
    enableNotificationsButton.addEventListener('click', function () {
      Notification.requestPermission().then(function (permission) {
        if (permission === 'granted') {
          showAlertNotification(lastAlertCount || 0);
          enableNotificationsButton.classList.add('d-none');
        }
      });
    });

    if (Notification.permission === 'granted') {
      enableNotificationsButton.classList.add('d-none');
    }
  }

  document.querySelectorAll('[data-preview-scope]').forEach(function (scope) {
    const rows = Array.from(scope.querySelectorAll('[data-preview-row]'));
    const filterButtons = Array.from(
      scope.querySelectorAll('[data-preview-filter]')
    );

    if (!rows.length || !filterButtons.length) {
      return;
    }

    function applyPreviewFilter(filter) {
      rows.forEach(function (row) {
        const state = row.dataset.alertState || 'clean';
        const visible = filter === 'all' || state === filter;
        row.classList.toggle('d-none', !visible);
      });

      filterButtons.forEach(function (button) {
        button.classList.toggle(
          'is-active',
          button.dataset.previewFilter === filter
        );
      });
    }

    filterButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        applyPreviewFilter(button.dataset.previewFilter || 'all');
      });
    });
  });
});
