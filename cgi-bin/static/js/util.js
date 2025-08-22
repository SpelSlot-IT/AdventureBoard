// Global Utility Module
(function(global) {
  let toastContainer = null;

  function showToast(message, type = 'error', customColor = null) {
    const typeConfig = {
      error:   { emoji: '❌', color: '#ff4d4f' },
      alert:   { emoji: '⚠️', color: '#faad14' },
      confirm: { emoji: '✅', color: '#52c41a' }
    };

    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'custom-toast-container';
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = 'custom-toast';

    let emoji = '';
    let color = customColor;
    if (typeConfig[type]) {
      emoji = typeConfig[type].emoji;
      color = color || typeConfig[type].color;
    }

    toast.textContent = `${emoji} ${message}`;
    toast.style.backgroundColor = color || '#ff4d4f';
    toastContainer.appendChild(toast);

    // Keep max 10 toasts
    if (toastContainer.children.length > 10) {
      const oldest = toastContainer.firstChild;
      oldest.classList.add('fade-out');
      setTimeout(() => oldest.remove(), 300);
    }

    // Show animation
    setTimeout(() => toast.classList.add('show'), 100);

    // Auto-remove
    setTimeout(() => {
      toast.classList.remove('show');
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 6000);
  }

  function escapeHtml(str) {
    if (str === undefined || str === null) return '';
    return String(str)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function truncate(str, len = 16) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len - 1) + '…' : str;
  }

  // Expose as global utility object
  global.Util = {
    showToast,
    escapeHtml,
    truncate
  };
})(window);
