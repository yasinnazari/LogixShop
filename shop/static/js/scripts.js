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

    function initializeNotification(notification) {
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
    }

    function initializeNotifications() {
        document.querySelectorAll(notificationSelector).forEach(initializeNotification);
    }

    window.showNotification = ({ message, type = 'success', icon = 'bi-check-circle-fill' }) => {
        let container = document.querySelector('.site-notifications');
        if (!container) {
            container = document.createElement('div');
            container.className = 'site-notifications';
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-atomic', 'false');
            document.body.appendChild(container);
        }

        while (container.querySelectorAll(notificationSelector).length >= 3) {
            container.querySelector(notificationSelector)?.remove();
        }

        const notification = document.createElement('div');
        const alertClass = {
            success: 'alert-success',
            error: 'alert-danger',
            warning: 'alert-warning',
            info: 'alert-info',
        }[type] || 'alert-info';
        notification.className = `alert ${alertClass} site-notification notification--${type}`;
        notification.dataset.notification = '';
        notification.dataset.notificationDuration = '15000';
        notification.setAttribute('role', 'alert');

        const content = document.createElement('div');
        content.className = 'notification-content';
        const iconElement = document.createElement('i');
        iconElement.className = `bi ${icon}`;
        iconElement.setAttribute('aria-hidden', 'true');
        const text = document.createElement('span');
        text.textContent = message;
        content.append(iconElement, text);

        const closeButton = document.createElement('button');
        closeButton.className = 'notification-close';
        closeButton.type = 'button';
        closeButton.dataset.notificationClose = '';
        closeButton.setAttribute('aria-label', 'Dismiss notification');
        closeButton.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';

        const progress = document.createElement('span');
        progress.className = 'notification-progress';
        progress.setAttribute('aria-hidden', 'true');

        notification.append(content, closeButton, progress);
        container.appendChild(notification);
        initializeNotification(notification);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeNotifications, { once: true });
    } else {
        initializeNotifications();
    }
})();
