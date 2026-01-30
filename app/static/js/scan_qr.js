document.addEventListener('DOMContentLoaded', function() {
    const successAudio = new Audio('https://actions.google.com/sounds/v1/science_fiction/scifi_laser_2.ogg');
    const errorAudio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');

    function onScanSuccess(decodedText, decodedResult) {
        html5QrCode.pause();
        updateStatus(true, "Đang kiểm tra dữ liệu...");

        fetch('/scan-checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qr_data: decodedText })
        })
        .then(response => response.json())
        .then(data => {
            showResult(data);
            setTimeout(() => {
                hideResult();
                updateStatus(false, "Sẵn sàng quét mã tiếp theo...");
                html5QrCode.resume();
            }, 3000);
        })
        .catch(err => {
            console.error(err);
            updateStatus(false, "Lỗi kết nối Server!");
            errorAudio.play().catch(()=>{});
            setTimeout(() => html5QrCode.resume(), 2000);
        });
    }

    function showResult(data) {
        const card = document.getElementById('resultCard');
        const nameEl = document.getElementById('resName');
        const statusEl = document.getElementById('resStatus');
        const msgEl = document.getElementById('resMsg');
        const timeEl = document.getElementById('resTime');

        card.style.display = 'block';
        if (data.success) {
            card.className = 'result-card success';
            nameEl.innerText = data.user.full_name;
            statusEl.className = `badge bg-${data.status_class}`;
            statusEl.innerText = data.status || 'Thành công';
            msgEl.innerText = data.message;
            timeEl.innerText = data.time;
            successAudio.play().catch(()=>{});
        } else {
            card.className = 'result-card error';
            nameEl.innerText = "Lỗi Check-in";
            statusEl.className = "badge bg-danger";
            statusEl.innerText = "Thất bại";
            msgEl.innerText = data.message;
            timeEl.innerText = "--:--";
            errorAudio.play().catch(()=>{});
        }
    }

    function hideResult() {
        document.getElementById('resultCard').style.display = 'none';
    }

    function updateStatus(isLoading, text) {
        const spinner = document.getElementById('loadingSpinner');
        const statusText = document.getElementById('statusText');
        spinner.style.display = isLoading ? 'inline-block' : 'none';
        statusText.innerText = text;
    }

    const html5QrCode = new Html5Qrcode("reader");
    const config = { fps: 10, qrbox: { width: 250, height: 250 } };
    
    html5QrCode.start(
        { facingMode: "environment" }, 
        config,
        onScanSuccess
    ).then(() => {
        updateStatus(false, "Sẵn sàng quét mã...");
    }).catch(err => {
        console.log("Lỗi Camera: ", err);
        updateStatus(false, "Không tìm thấy Camera!");
    });
});