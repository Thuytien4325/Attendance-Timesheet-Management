function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    const clockElement = document.getElementById('clock');
    if(clockElement) clockElement.textContent = `${hours}:${minutes}:${seconds}`;

    const days = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
    const dateElement = document.getElementById('date');
    if(dateElement) dateElement.textContent = `${days[now.getDay()]}, ${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
    
    const miniClock = document.getElementById('currentTime');
    if(miniClock) miniClock.innerHTML = `<i class="fas fa-clock"></i> ${hours}:${minutes}:${seconds}`;
}
setInterval(updateClock, 1000);
updateClock();

// ------------------------------
// Anchor navigation (e.g. /dashboard#history)
// In this UI, main content can live inside a scrollable container.
// Default browser hash scrolling is unreliable in that case, so we
// proactively scroll the target element into view.
// ------------------------------
function scrollToHashTarget() {
    const hash = window.location.hash;
    if (!hash || hash.length < 2) return;

    const id = hash.substring(1);
    const target = document.getElementById(id);
    if (!target) return;

    // Wait for layout to settle (Bootstrap collapse, sidebar animation, etc.)
    window.requestAnimationFrame(() => {
        try {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } catch (e) {
            // Fallback for older browsers
            target.scrollIntoView(true);
        }
    });
}

window.addEventListener('hashchange', scrollToHashTarget);
document.addEventListener('DOMContentLoaded', scrollToHashTarget);

// Sidebar Mobile Logic
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');
if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('show');
        overlay.classList.toggle('show');
    });
}
if (overlay) {
    overlay.addEventListener('click', function() {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
    });
}

// When clicking a hash link in the sidebar on mobile,
// close the sidebar so the content is visible.
document.addEventListener('click', function (e) {
    const link = e.target && e.target.closest ? e.target.closest('a') : null;
    if (!link) return;

    const href = link.getAttribute('href') || '';
    if (!href.includes('#')) return;

    // Only handle same-page hashes (or dashboard hash links)
    if (href.endsWith('#history') || href === '#history') {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
        // Let navigation happen, then scroll
        setTimeout(scrollToHashTarget, 50);
    }
});