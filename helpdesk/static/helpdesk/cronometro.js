document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.cronometro-display').forEach(function (display) {
        const running = display.dataset.running === 'true';
        let totalSeconds = Number.parseInt(display.dataset.seconds || '0', 10);
        if (!running) return;

        window.setInterval(function () {
            totalSeconds += 1;
            const hours = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
            const minutes = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
            const seconds = (totalSeconds % 60).toString().padStart(2, '0');
            display.textContent = `⏳ ${hours}:${minutes}:${seconds} (RODANDO)`;
        }, 1000);
    });
});
