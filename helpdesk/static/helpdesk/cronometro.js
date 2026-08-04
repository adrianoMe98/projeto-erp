document.addEventListener('DOMContentLoaded', function() {
    // Procura a nossa etiqueta HTML na tela
    const display = document.getElementById('cronometro-display');
    
    if (display) {
        // Verifica se o ticket está "Em Andamento"
        const rodando = display.getAttribute('data-rodando') === 'true';
        let segundosTotais = parseInt(display.getAttribute('data-segundos'));
        
        if (rodando) {
            // Cria um loop que roda a cada 1000 milissegundos (1 segundo)
            setInterval(function() {
                segundosTotais++;
                
                let horas = Math.floor(segundosTotais / 3600);
                let minutos = Math.floor((segundosTotais % 3600) / 60);
                let segundos = segundosTotais % 60;
                
                // Formata os números para sempre terem 2 casas (ex: 09 ao invés de 9)
                let hStr = horas.toString().padStart(2, '0');
                let mStr = minutos.toString().padStart(2, '0');
                let sStr = segundos.toString().padStart(2, '0');
                
                // Atualiza o relógio na tela
                display.innerHTML = `⏳ ${hStr}:${mStr}:${sStr} (▶️ RODANDO)`;
            }, 1000);
        }
    }
});