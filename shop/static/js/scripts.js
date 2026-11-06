(() => {
  const notificationSelector = '[data-notification]';
  const closeSelector = '[data-notification-close]';
  const dismissalDuration = 350;

  function dismissNotification(notification) {
    if (notification.dataset.dismissed === 'true') {
      return;
    }

    notification.dataset.dismissed = 'true';
    notification.classList.add('is-dismissing');

    window.setTimeout(() => {
      notification.remove();
    }, dismissalDuration);
  }

  function initializeNotifications() {
    document.querySelectorAll(notificationSelector).forEach((notification) => {
      const duration = Number(notification.dataset.notificationDuration) || 15000;
      const closeButton = notification.querySelector(closeSelector);

      notification.style.setProperty('--notification-duration', `${duration}ms`);
      notification.notificationTimer = window.setTimeout(() => {
        dismissNotification(notification);
      }, duration);

      closeButton?.addEventListener('click', () => {
        window.clearTimeout(notification.notificationTimer);
        dismissNotification(notification);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeNotifications, { once: true });
  } else {
    initializeNotifications();
  }
})();
