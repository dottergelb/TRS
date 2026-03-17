(function () {
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  const levelToType = (level) => {
    const v = (level || '').toLowerCase();
    if (v.includes('error') || v.includes('danger')) return 'danger';
    if (v.includes('success')) return 'success';
    if (v.includes('warning')) return 'warning';
    return 'info';
  };

  function toast(message, level = 'info', timeoutMs = 3500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const type = levelToType(level);
    const node = el('div', `toast toast--${type}`);
    node.appendChild(el('div', 'toast__title',
      type === 'success' ? 'Готово' : type === 'danger' ? 'Ошибка' : type === 'warning' ? 'Внимание' : 'Сообщение'
    ));
    node.appendChild(el('div', 'toast__msg', message));

    const close = el('button', 'toast__close', '×');
    close.type = 'button';
    close.addEventListener('click', () => node.remove());
    node.appendChild(close);

    container.appendChild(node);
    requestAnimationFrame(() => node.classList.add('toast--show'));
    window.setTimeout(() => {
      node.classList.remove('toast--show');
      window.setTimeout(() => node.remove(), 200);
    }, timeoutMs);
  }

  // Expose a tiny public API for templates that want to use it
  window.AppUI = window.AppUI || {};
  window.AppUI.toast = toast;

  document.addEventListener('DOMContentLoaded', () => {
    // Convert Django messages (seeded in base.html) into toasts
    const seed = document.querySelector('.js-toast-seed');
    if (seed) {
      seed.querySelectorAll('.js-toast').forEach((n) => {
        const msg = n.getAttribute('data-message') || '';
        const lvl = n.getAttribute('data-level') || 'info';
        if (msg) toast(msg, lvl);
      });
    }
  });
})();
