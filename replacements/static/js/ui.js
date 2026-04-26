(function () {
  let initialized = false;
  let unreadTimer = null;
  let prevUnreadMessages = null;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function levelToType(level) {
    const value = (level || '').toLowerCase();
    if (value.includes('error') || value.includes('danger')) return 'danger';
    if (value.includes('success')) return 'success';
    if (value.includes('warning')) return 'warning';
    return 'info';
  }

  function toastTitle(type) {
    if (type === 'success') return 'Готово';
    if (type === 'danger') return 'Ошибка';
    if (type === 'warning') return 'Внимание';
    return 'Сообщение';
  }

  function toast(message, level, timeoutMs) {
    const duration = Number.isFinite(timeoutMs) ? timeoutMs : 3500;
    const container = document.getElementById('toastContainer');
    if (!container || !message) return;

    const type = levelToType(level || 'info');
    const node = el('div', 'toast');
    node.classList.add('toast--' + type);
    node.appendChild(el('div', 'toast__title', toastTitle(type)));
    node.appendChild(el('div', 'toast__msg', String(message)));

    const close = el('button', 'toast__close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', 'Закрыть уведомление');
    close.addEventListener('click', () => node.remove());
    node.appendChild(close);

    container.appendChild(node);
    window.setTimeout(() => node.remove(), duration);
  }

  function markActiveSidebarLinks() {
    const links = document.querySelectorAll('.app-sidebar__link[href]');
    if (!links.length) return;

    const current = window.location.pathname.replace(/\/+$/, '');
    links.forEach((link) => {
      const href = (link.getAttribute('href') || '').replace(/\/+$/, '');
      if (href && href === current) {
        link.classList.add('is-active');
        link.setAttribute('aria-current', 'page');
      }
    });
  }

  function bindSidebar() {
    if (document.body && document.body.dataset.sidebarBound === '1') return;
    const body = document.body;
    const toggle = document.getElementById('sidebarToggle');
    const closeBtn = document.getElementById('sidebarClose');
    const backdrop = document.getElementById('sidebarBackdrop');
    const links = document.querySelectorAll('.app-sidebar__link');
    if (!toggle || !backdrop) return;

    const setOpen = (open) => {
      body.classList.toggle('sidebar-open', !!open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    };

    toggle.addEventListener('click', () => setOpen(!body.classList.contains('sidebar-open')));
    if (closeBtn) closeBtn.addEventListener('click', () => setOpen(false));
    backdrop.addEventListener('click', () => setOpen(false));
    links.forEach((link) => link.addEventListener('click', () => setOpen(false)));
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') setOpen(false);
    });
    if (body) body.dataset.sidebarBound = '1';
  }

  function applyRandomNavAnimal() {
    const icon = document.querySelector('.nav-user__icon');
    if (!icon) return;
    if (icon.dataset && icon.dataset.fixed === '1') return;

    const animals = ['🦊', '🐼', '🦉', '🐯', '🦁', '🐻', '🐨', '🐸', '🐬', '🦄', '🐧', '🦋', '🐿️', '🦝', '🐢', '🦔'];
    let last = '';
    try {
      last = window.localStorage.getItem('nav_user_animal') || '';
    } catch (e) {}

    let next = animals[Math.floor(Math.random() * animals.length)];
    if (animals.length > 1 && next === last) {
      const idx = (animals.indexOf(next) + 1 + Math.floor(Math.random() * (animals.length - 1))) % animals.length;
      next = animals[idx];
    }

    icon.textContent = next;
    try {
      window.localStorage.setItem('nav_user_animal', next);
    } catch (e) {}
  }

  function applyTopOffset() {
    const topNav = document.querySelector('.top-nav');
    if (!topNav) return;
    const height = topNav.offsetHeight || 60;
    document.documentElement.style.setProperty('--top-nav-height', height + 'px');
  }

  function bootSeedToasts() {
    const seed = document.querySelector('.js-toast-seed');
    if (!seed) return;

    seed.querySelectorAll('.js-toast').forEach((entry) => {
      const msg = entry.getAttribute('data-message') || '';
      const level = entry.getAttribute('data-level') || 'info';
      if (msg) toast(msg, level);
    });
  }

  window.AppUI = window.AppUI || {};
  window.AppUI.toast = toast;
  window.AppUI.playMessageTone = playIncomingMessageTone;

  function playIncomingMessageTone() {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    try {
      const audioCtx = new Ctx();
      const oscillator = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(660, audioCtx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.06, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.18);

      oscillator.connect(gain);
      gain.connect(audioCtx.destination);
      oscillator.start(audioCtx.currentTime);
      oscillator.stop(audioCtx.currentTime + 0.18);

      window.setTimeout(() => {
        audioCtx.close().catch(() => {});
      }, 260);
    } catch (e) {}
  }

  function setUnreadBadge(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    const n = Number(value) || 0;
    if (n > 0) {
      el.hidden = false;
      el.textContent = n > 99 ? '99+' : String(n);
    } else {
      el.hidden = true;
      el.textContent = '0';
    }
  }

  function setUnreadPulse(linkId, value) {
    const link = document.getElementById(linkId);
    if (!link) return;
    const has = (Number(value) || 0) > 0;
    link.classList.toggle('has-unread', has);
  }

  function applyUnreadCounts(payload) {
    const messages = Number(payload && payload.messages) || 0;
    const notifications = Number(payload && payload.notifications) || 0;

    if (prevUnreadMessages !== null && messages > prevUnreadMessages) {
      const added = messages - prevUnreadMessages;
      toast(added > 1 ? `Новых сообщений: ${added}` : 'Новое сообщение', 'info', 3200);
      playIncomingMessageTone();
    }
    prevUnreadMessages = messages;

    setUnreadBadge('navUnreadMessagesCount', messages);
    setUnreadBadge('sidebarUnreadMessagesCount', messages);
    setUnreadBadge('navUnreadNotificationsCount', notifications);
    setUnreadBadge('sidebarUnreadNotificationsCount', notifications);

    setUnreadPulse('navMsgLink', messages);
    setUnreadPulse('sidebarMsgLink', messages);
    setUnreadPulse('navNotifLink', notifications);
    setUnreadPulse('sidebarNotifLink', notifications);
  }

  async function fetchUnreadCounts() {
    const hasTargets = document.getElementById('navUnreadMessagesCount')
      || document.getElementById('sidebarUnreadMessagesCount')
      || document.getElementById('navUnreadNotificationsCount')
      || document.getElementById('sidebarUnreadNotificationsCount');
    if (!hasTargets) return;
    try {
      const response = await fetch('/comm/api/unread/', { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) return;
      const data = await response.json();
      applyUnreadCounts(data);
    } catch (e) {}
  }

  function startUnreadPolling() {
    if (unreadTimer) return;
    fetchUnreadCounts();
    unreadTimer = window.setInterval(fetchUnreadCounts, 5000);
  }

  function initUI() {
    if (initialized) return;
    initialized = true;
    applyTopOffset();
    applyRandomNavAnimal();
    markActiveSidebarLinks();
    bindSidebar();
    bootSeedToasts();
    startUnreadPolling();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUI, { once: true });
  } else {
    initUI();
  }
  window.addEventListener('resize', applyTopOffset);
  window.addEventListener('focus', fetchUnreadCounts);
})();
