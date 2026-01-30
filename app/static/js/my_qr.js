function refreshQR() {
    const img = document.getElementById('qrCodeImage');
    const currentSrc = img.src.split('?')[0];
    img.src = currentSrc + '?t=' + new Date().getTime();
}

function downloadQR() {
    const img = document.getElementById('qrCodeImage');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    ctx.drawImage(img, 0, 0);
    
    canvas.toBlob(function(blob) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'my-qr-code.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    });
}