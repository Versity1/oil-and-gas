function toggleMenu() {
    const menu = document.getElementById('offcanvas-menu');
    if (!menu) return;

    const sidebar = menu.querySelector('div');

    if (menu.classList.contains('opacity-0')) {
        // Open
        menu.classList.remove('opacity-0', 'pointer-events-none');
        setTimeout(() => {
            if (sidebar) sidebar.classList.remove('translate-x-full');
        }, 10);
    } else {
        // Close
        if (sidebar) sidebar.classList.add('translate-x-full');
        setTimeout(() => {
            menu.classList.add('opacity-0', 'pointer-events-none');
        }, 300);
    }
}

// Close on click outside
const offcanvasMenuDb = document.getElementById('offcanvas-menu');
if (offcanvasMenuDb) {
    offcanvasMenuDb.addEventListener('click', function (e) {
        if (e.target === this) {
            toggleMenu();
        }
    });
}

// Notification System
function initNotifications() {
    const notificationBtn = document.getElementById('notification-btn');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationList = document.getElementById('notification-list');
    const notificationBadge = document.getElementById('notification-badge');
    const markAllReadBtn = document.getElementById('mark-all-read-btn');
    const container = document.getElementById('notification-container');

    if (!notificationBtn || !notificationPanel) return;

    let notificationsOpen = false;

    function toggleNotificationPanel() {
        if (notificationsOpen) {
            closeNotificationPanel();
        } else {
            openNotificationPanel();
        }
    }

    function openNotificationPanel() {
        notificationPanel.classList.remove('opacity-0', 'invisible', 'translate-y-2');
        notificationPanel.classList.add('opacity-100', 'visible', 'translate-y-0');
        notificationsOpen = true;
        fetchNotifications();
    }

    function closeNotificationPanel() {
        notificationPanel.classList.add('opacity-0', 'invisible', 'translate-y-2');
        notificationPanel.classList.remove('opacity-100', 'visible', 'translate-y-0');
        notificationsOpen = false;
    }

    // Toggle on button click
    notificationBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleNotificationPanel();
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (notificationsOpen && container && !container.contains(e.target)) {
            closeNotificationPanel();
        }
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && notificationsOpen) {
            closeNotificationPanel();
        }
    });

    // Mark all read
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent closing
            markAllAsRead();
        });
    }

    function getNotificationIcon(type) {
        const icons = {
            'info': 'info',
            'success': 'check_circle',
            'warning': 'warning',
            'profit': 'trending_up'
        };
        return icons[type] || 'notifications';
    }

    function getNotificationColor(type) {
        const colors = {
            'info': 'text-blue-500',
            'success': 'text-green-500',
            'warning': 'text-yellow-500',
            'profit': 'text-emerald-500'
        };
        return colors[type] || 'text-primary';
    }

    async function fetchNotifications() {
        if (!notificationList) return;

        try {
            const response = await fetch('/api/notifications/');
            if (!response.ok) throw new Error('Failed to fetch');

            const data = await response.json();
            renderNotifications(data.notifications);
            updateBadge(data.unread_count);
        } catch (error) {
            console.error('Notification fetch error:', error);
            notificationList.innerHTML = `
                <div class="p-6 text-center text-text-sec-light dark:text-text-sec-dark text-sm">
                    <span class="material-symbols-outlined text-3xl mb-2 block opacity-50">error</span>
                    Failed to load notifications
                </div>
            `;
        }
    }

    function renderNotifications(notifications) {
        if (!notificationList) return;

        if (notifications.length === 0) {
            notificationList.innerHTML = `
                <div class="p-6 text-center text-text-sec-light dark:text-text-sec-dark text-sm">
                    <span class="material-symbols-outlined text-3xl mb-2 block opacity-50">notifications_off</span>
                    No notifications yet
                </div>
            `;
            return;
        }

        notificationList.innerHTML = notifications.map(n => `
            <div class="flex gap-3 p-4 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer ${n.is_read ? 'opacity-60' : ''}" data-notification-id="${n.id}">
                <div class="flex-shrink-0">
                    <span class="material-symbols-outlined ${getNotificationColor(n.type)}">${getNotificationIcon(n.type)}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-text-main-light dark:text-text-main-dark ${n.is_read ? '' : 'font-bold'}">${n.title}</p>
                    <p class="text-xs text-text-sec-light dark:text-text-sec-dark mt-0.5 truncate">${n.message}</p>
                    <p class="text-[10px] text-text-sec-light dark:text-text-sec-dark mt-1 opacity-70">${n.created_at}</p>
                </div>
                ${!n.is_read ? '<span class="w-2 h-2 bg-primary rounded-full flex-shrink-0 mt-1.5"></span>' : ''}
            </div>
        `).join('');

        // Add click handlers to mark as read
        notificationList.querySelectorAll('[data-notification-id]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent closing panel immediately? actually we might want to keep it open or close it. 
                // Let's keep it open but update UI
                markAsRead(item.dataset.notificationId);
            });
        });
    }

    function updateBadge(count) {
        if (!notificationBadge) return;

        if (count > 0) {
            notificationBadge.textContent = count > 99 ? '99+' : count;
            notificationBadge.classList.remove('hidden');
            notificationBadge.classList.add('animate-pulse');
        } else {
            notificationBadge.classList.add('hidden');
            notificationBadge.classList.remove('animate-pulse');
        }
    }

    async function markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                // Refresh list to update UI state
                fetchNotifications();
            }
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
        }
    }

    async function markAllAsRead() {
        try {
            const response = await fetch('/api/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                fetchNotifications();
            }
        } catch (error) {
            console.error('Failed to mark all notifications as read:', error);
        }
    }

    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    // Initial fetch
    fetchNotifications();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initNotifications);
