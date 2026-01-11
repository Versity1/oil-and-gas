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
