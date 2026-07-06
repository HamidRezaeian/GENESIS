const canvas = document.getElementById('ramCanvas');
const ctx = canvas.getContext('2d', { alpha: false });

// For pixelated look
canvas.style.imageRendering = 'pixelated';

let world_w = 64;
let world_h = 64;
let imgData = null;

let chartInstance = null;

function initChart() {
    const ctxChart = document.getElementById('extinctionChart').getContext('2d');
    chartInstance = new Chart(ctxChart, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Era Lifespan (Cycles)',
                data: [],
                borderColor: '#FF0055',
                backgroundColor: 'rgba(255, 0, 85, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: { 
                    grid: { color: 'rgba(255,255,255,0.05)' }, 
                    ticks: { color: '#4B5563', maxTicksLimit: 5 } 
                },
                y: { 
                    grid: { color: 'rgba(255,255,255,0.05)' }, 
                    ticks: { 
                        color: '#4B5563', 
                        callback: function(value) {
                            return (value / 1000).toFixed(1) + 'K';
                        }
                    }
                }
            },
            plugins: {
                legend: { labels: { color: '#9CA3AF' } }
            }
        }
    });
}

function updateChart(history) {
    if (!chartInstance) return;
    
    chartInstance.data.labels = history.map(h => Math.floor(h.tick / 1000) + 'k');
    chartInstance.data.datasets[0].data = history.map(h => h.rate);
    chartInstance.update();
}

async function fetchState() {
    try {
        const response = await fetch('http://localhost:8081/api/state');
        const state = await response.json();

        // Ensure canvas dimensions match world exactly for 1:1 pixel mapping
        if (canvas.width !== state.world_w || canvas.height !== state.world_h) {
            world_w = state.world_w;
            world_h = state.world_h;
            canvas.width = world_w;
            canvas.height = world_h;
            imgData = ctx.createImageData(world_w, world_h);
        }

        // Update KPIs
        document.getElementById('val-cycles').innerText = state.tick.toLocaleString();
        document.getElementById('val-pop').innerHTML = `${state.pop.toLocaleString()} <span class="dim">/ ${state.max_pop}</span>`;
        document.getElementById('val-extinctions').innerText = state.extinctions.toLocaleString();
        if (state.elite_age !== undefined) {
            document.getElementById('val-maxage').innerHTML = `${state.elite_age.toLocaleString()} <span class="dim">ticks</span>`;
        }
        if (state.elite_iq !== undefined) {
            document.getElementById('val-iq').innerHTML = `${state.elite_iq} <span class="dim">%</span>`;
        }

        updateChart(state.ext_history);

        if (state.food_b64 && imgData) {
            // Decode Base64 string to raw binary string
            const binaryString = atob(state.food_b64);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Map the byte array to a Float32Array
            const foodGrid = new Float32Array(bytes.buffer);
            
            const pixels = imgData.data;
            const sz = world_w * world_h;

            // Render Food Grid (Green)
            for (let i = 0; i < sz; i++) {
                const food = foodGrid[i]; // 0 to 255
                const greenInt = Math.min(255, Math.floor(food));
                
                // Base background is dark cyan/gray
                let r = 10;
                let g = 20;
                let b = 30;
                
                if (greenInt > 0) {
                    r = 10;
                    g = greenInt;
                    b = 30;
                }

                const pxIdx = i * 4;
                pixels[pxIdx] = r;
                pixels[pxIdx + 1] = g;
                pixels[pxIdx + 2] = b;
                pixels[pxIdx + 3] = 255;
            }

            // Render Organisms (Hot Pink)
            const orgs = state.orgs;
            for (let i = 0; i < orgs.length; i++) {
                const pos = orgs[i];
                if (pos >= 0 && pos < sz) {
                    const pxIdx = pos * 4;
                    pixels[pxIdx] = 255;     // R
                    pixels[pxIdx + 1] = 0;   // G
                    pixels[pxIdx + 2] = 85;  // B
                    pixels[pxIdx + 3] = 255; // A
                }
            }

            ctx.putImageData(imgData, 0, 0);
        }

    } catch (e) {
        console.error("API Error", e);
    }
}

initChart();

// =========================================================================
// Brain Analyzer Modal Logic
// =========================================================================

const btnAnalyze = document.getElementById('btn-analyze');
const modal = document.getElementById('brain-modal');
const btnClose = document.getElementById('btn-close-modal');
const brainData = document.getElementById('brain-data');

btnAnalyze.addEventListener('click', async () => {
    modal.classList.remove('hidden');
    brainData.innerHTML = "<p>Extracting Elite DNA from the Ark...</p>";
    
    try {
        const res = await fetch('/api/analyze');
        const data = await res.json();
        
        if (data.status === 'extinct') {
            brainData.innerHTML = "<p style='color: var(--color-red);'>Universe is currently completely extinct. Waiting for panspermia (reseeding)... Try again in a few seconds.</p>";
            return;
        }
        
        let html = `
            <div style="margin-bottom: 20px; display: flex; align-items: center; flex-wrap: wrap;">
                <span class="badge glow-cyan" title="Population of this exact DNA">Pop: ${data.population}</span>
                <span class="badge" title="Unique active DNA strings">Species: ${data.species}</span>
                <span class="badge" title="Maximum age reached by this DNA" style="border-color: #00FF9D; color: #00FF9D;">Max Age: ${data.max_age}</span>
                <span class="iq-badge" title="Foraging IQ Score">IQ: ${data.iq}%</span>
            </div>
            <div style="font-family: monospace; font-size: 0.8rem; margin-bottom: 12px; color: #888;">
                DNA Hash: ${data.hex}...
            </div>
            
            <div class="iq-results">
                <div style="color: #B200FF; font-weight: bold; margin-bottom: 8px;">VIRTUAL SANDBOX EVALUATION</div>
                ${data.test_results.map(r => `
                    <div class="iq-scenario">
                        <span>[Scenario] ${r.scenario}</span>
                        <span>
                            <span style="color: #aaa; font-size: 0.8rem; margin-right: 10px;">&rarr; ${r.action}</span>
                            <span class="${r.passed ? 'iq-pass' : 'iq-fail'}">${r.passed ? 'PASS' : 'FAIL'}</span>
                        </span>
                    </div>
                `).join('')}
            </div>

            <div class="brain-grid">
                <div class="synapse-list">
                    <h3 style="color: #00E5FF; margin-bottom: 12px; font-size: 1rem;">Sensory &rarr; Hidden</h3>
                    ${data.synapses.filter(s => s.source.includes('Food') || s.source.includes('Energy') || s.source.includes('Crowding'))
                        .sort((a,b) => Math.abs(b.weight) - Math.abs(a.weight))
                        .map(s => {
                            const cls = s.weight > 0 ? 'excitatory' : 'inhibitory';
                            const sign = s.weight > 0 ? '+' : '';
                            return `<div class="synapse-item">
                                <span>${s.source} &rarr; ${s.target}</span>
                                <span class="synapse-weight ${cls}">${sign}${s.weight.toFixed(2)}</span>
                            </div>`;
                        }).join('') || '<div class="synapse-item">No strong synapses</div>'}
                </div>
                <div class="synapse-list">
                    <h3 style="color: #FF4E00; margin-bottom: 12px; font-size: 1rem;">Hidden &rarr; Motor</h3>
                    ${data.synapses.filter(s => !s.source.includes('Food') && !s.source.includes('Energy') && !s.source.includes('Crowding'))
                        .sort((a,b) => Math.abs(b.weight) - Math.abs(a.weight))
                        .map(s => {
                            const cls = s.weight > 0 ? 'excitatory' : 'inhibitory';
                            const sign = s.weight > 0 ? '+' : '';
                            return `<div class="synapse-item">
                                <span>${s.source} &rarr; ${s.target}</span>
                                <span class="synapse-weight ${cls}">${sign}${s.weight.toFixed(2)}</span>
                            </div>`;
                        }).join('') || '<div class="synapse-item">No strong synapses</div>'}
                </div>
            </div>
        `;
        brainData.innerHTML = html;
        
    } catch (err) {
        brainData.innerHTML = `<p style='color: var(--color-red);'>Failed to fetch brain data.</p>`;
    }
});

btnClose.addEventListener('click', () => {
    modal.classList.add('hidden');
});

// Update every 100ms
setInterval(fetchState, 100);
