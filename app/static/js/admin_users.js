// Xử lý xóa nhân viên bằng POST request với fetch API
document.addEventListener('DOMContentLoaded', function() {
    // Lắng nghe sự kiện click trên các nút xóa
    const deleteButtons = document.querySelectorAll('.btn-delete-user');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const userId = this.getAttribute('data-user-id');
            const userName = this.getAttribute('data-user-name');
            const buttonElement = this;
            
            if (confirm(`CẢNH BÁO: Bạn có chắc chắn muốn xóa nhân viên "${userName}"?\nHành động này không thể hoàn tác!`)) {
                // Vô hiệu hóa nút trong khi xử lý
                buttonElement.disabled = true;
                buttonElement.innerHTML = '<i class="bi bi-hourglass-split"></i> Đang xóa...';
                
                // Gửi POST request bằng fetch API
                fetch(`/admin/user/delete/${userId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Hiển thị thông báo thành công
                        const alertDiv = document.createElement('div');
                        alertDiv.className = 'alert alert-success alert-dismissible fade show';
                        alertDiv.innerHTML = `
                            <i class="bi bi-check-circle-fill me-2"></i>${data.message || 'Xóa nhân viên thành công!'}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        `;
                        // Chèn thông báo vào đầu container
                        const container = document.querySelector('.container');
                        container.insertBefore(alertDiv, container.firstChild);
                        
                        // Xóa dòng khỏi bảng ngay lập tức
                        const row = buttonElement.closest('tr');
                        if (row) row.remove();
                        
                        // Reload trang sau 1 giây để cập nhật danh sách sạch sẽ
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    } else {
                        // Hiển thị thông báo lỗi
                        const alertDiv = document.createElement('div');
                        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
                        alertDiv.innerHTML = `
                            <i class="bi bi-exclamation-triangle-fill me-2"></i>${data.message || 'Có lỗi xảy ra khi xóa nhân viên!'}
                            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                        `;
                        document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
                        
                        // Khôi phục nút
                        buttonElement.disabled = false;
                        buttonElement.innerHTML = '<i class="bi bi-trash-fill"></i> Xóa';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
                    alertDiv.innerHTML = `
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>Lỗi kết nối hệ thống!
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
                    
                    // Khôi phục nút
                    buttonElement.disabled = false;
                    buttonElement.innerHTML = '<i class="bi bi-trash-fill"></i> Xóa';
                });
            }
        });
    });

    // --- ĐOẠN MÃ THÊM MỚI: XỬ LÝ HIỆU ỨNG NÚT XUẤT EXCEL ---
    const exportBtn = document.querySelector('a[href*="export_attendance"]');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            const originalContent = this.innerHTML;
            // Hiển thị trạng thái đang xử lý khi Admin nhấn xuất
            this.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Đang chuẩn bị file...';
            this.classList.add('disabled');
            this.style.pointerEvents = 'none';

            // Khôi phục nút sau khi trình duyệt bắt đầu tải file
            setTimeout(() => {
                this.innerHTML = originalContent;
                this.classList.remove('disabled');
                this.style.pointerEvents = 'auto';
            }, 3000);
        });
    }
});