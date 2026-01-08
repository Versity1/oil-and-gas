const offcanvasMenu = document.getElementById('offcanvas-menu');
const menuToggle = document.getElementById('menu-toggle');
const closeMenu = document.getElementById('close-menu');
const menuLinks = document.querySelectorAll('#offcanvas-menu a');

function openMenu() {
    if (!offcanvasMenu) return;
    offcanvasMenu.classList.remove('opacity-0', 'pointer-events-none');
    const sidebar = offcanvasMenu.querySelector('div');
    if (sidebar) sidebar.classList.remove('translate-x-full');
    document.body.style.overflow = 'hidden';
}

function closeMenuFunc() {
    if (!offcanvasMenu) return;
    offcanvasMenu.classList.add('opacity-0', 'pointer-events-none');
    const sidebar = offcanvasMenu.querySelector('div');
    if (sidebar) sidebar.classList.add('translate-x-full');
    document.body.style.overflow = '';
}

if (menuToggle) menuToggle.addEventListener('click', openMenu);
if (closeMenu) closeMenu.addEventListener('click', closeMenuFunc);
if (menuLinks) menuLinks.forEach(link => link.addEventListener('click', closeMenuFunc));

if (offcanvasMenu) {
    offcanvasMenu.addEventListener('click', e => { 
        if (e.target === offcanvasMenu) closeMenuFunc(); 
    });
}

document.addEventListener('keydown', e => { 
    if (e.key === 'Escape') closeMenuFunc(); 
});
