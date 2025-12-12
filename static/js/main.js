// --- 1. ĐỒNG HỒ THỜI GIAN THỰC ---
function updateClock() {
    const now = new Date();
    
    // Giờ:Phút:Giây
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const clockElement = document.getElementById('clock');
    if(clockElement) {
        clockElement.textContent = `${hours}:${minutes}:${seconds}`;
    }

    // Ngày tháng
    const days = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
    const day = days[now.getDay()];
    const date = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    const dateElement = document.getElementById('date');
    if(dateElement) {
        dateElement.textContent = `${day}, ${date}/${month}/${year}`;
    }
}

// Cập nhật mỗi giây
updateClock();
setInterval(updateClock, 1000);

// --- 2. XỬ LÝ SIDEBAR TRÊN MOBILE ---
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

// --- 3. HIỆU ỨNG MENU ACTIVE ---
document.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', function(e) {
        // Xóa class active ở tất cả các item
        document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active'));
        // Thêm class active vào item đang click
        this.classList.add('active');
    });
});