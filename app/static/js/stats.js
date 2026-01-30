// public/js/stats.js

document.addEventListener('DOMContentLoaded', function() {
    loadDashboardCharts();
});

async function loadDashboardCharts() {
    try {
        // 1. Gọi API lấy dữ liệu
        const response = await fetch('/api/stats');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (!result.success) {
            console.error('API trả về lỗi:', result.error);
            return;
        }

        // Lấy dữ liệu từ API
        const { pieChart: pieData, barChart: barData } = result;

        // 2. Vẽ Biểu Đồ Tròn (Pie Chart)
        renderPieChart(pieData);

        // 3. Vẽ Biểu Đồ Cột (Bar Chart)
        renderBarChart(barData);

    } catch (error) {
        console.error("Lỗi khi tải biểu đồ:", error);
    }
}

// Hàm vẽ biểu đồ tròn
function renderPieChart(data) {
    const ctx = document.getElementById('pieChart').getContext('2d');
    
    // Kiểm tra nếu không có dữ liệu
    if (data.on_time === 0 && data.late === 0 && data.absent === 0) {
        // Có thể hiển thị thông báo "Chưa có dữ liệu" nếu cần
    }

    new Chart(ctx, {
        type: 'doughnut', // Kiểu biểu đồ bánh Donut
        data: {
            labels: ['Đúng giờ', 'Đi muộn', 'Vắng mặt'],
            datasets: [{
                data: [data.on_time, data.late, data.absent],
                backgroundColor: [
                    '#28a745', // Xanh lá
                    '#ffc107', // Vàng
                    '#dc3545'  // Đỏ
                ],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Để CSS kiểm soát chiều cao
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                }
            }
        }
    });
}

// Hàm vẽ biểu đồ cột
function renderBarChart(dataList) {
    const ctx = document.getElementById('barChart').getContext('2d');

    // Tách dữ liệu từ mảng object API trả về
    const labels = dataList.map(item => item.date); // Ngày tháng
    const values = dataList.map(item => item.count); // Số lượng người

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Nhân viên đi làm',
                data: values,
                backgroundColor: 'rgba(54, 162, 235, 0.7)', // Màu xanh dương nhạt
                borderColor: 'rgba(54, 162, 235, 1)',       // Viền xanh đậm
                borderWidth: 1,
                borderRadius: 5 // Bo tròn góc cột
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1 // Chỉ hiện số nguyên (người)
                    },
                    grid: {
                        color: '#f0f0f0' // Màu lưới mờ
                    }
                },
                x: {
                    grid: {
                        display: false // Ẩn lưới dọc
                    }
                }
            },
            plugins: {
                legend: {
                    display: false // Ẩn chú thích vì chỉ có 1 loại dữ liệu
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` ${context.raw} nhân viên`;
                        }
                    }
                }
            }
        }
    });
}