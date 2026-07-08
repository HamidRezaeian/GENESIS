const canvas = document.getElementById('ramCanvas');
const ctx = canvas.getContext('2d', { alpha: false });

// For pixelated look
canvas.style.imageRendering = 'pixelated';

let world_w = 256;
let world_h = 256;
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

        // Check if canvas matches 256x256
        if (!imgData || canvas.width !== 256) {
            world_w = 256;
            world_h = 256;
            canvas.width = 256;
            canvas.height = 256;
            imgData = ctx.createImageData(256, 256);
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
        if (state.avg_age !== undefined) {
            document.getElementById('val-avgage').innerHTML = `${state.avg_age.toLocaleString()} <span class="dim">ticks</span>`;
        }

        updateChart(state.ext_history);

        if (state.ram_b64 && imgData) {
            const binaryString = atob(state.ram_b64);
            const len = binaryString.length;
            const pixels = imgData.data;

            for (let i = 0; i < len; i++) {
                const val = binaryString.charCodeAt(i);
                const pxIdx = i * 4;
                
                // Base background is dark cyan/gray
                let r = 10;
                let g = 20;
                let b = 30;

                if (val === 0x55) {
                    // Energy: Green
                    r = 0; g = 255; b = 157;
                } else if (val === 0xFF) {
                    // Trap: Red
                    r = 255; g = 0; b = 85;
                }

                pixels[pxIdx] = r;
                pixels[pxIdx + 1] = g;
                pixels[pxIdx + 2] = b;
                pixels[pxIdx + 3] = 255;
            }

            // Render Organisms (Blue normally, Yellow if Screaming)
            const orgs = state.orgs;
            const screamingOrgs = new Set(state.screaming_orgs || []);
            for (let i = 0; i < orgs.length; i++) {
                const pos = orgs[i];
                if (pos >= 0 && pos < len) {
                    const pxIdx = pos * 4;
                    if (screamingOrgs.has(pos)) {
                        // Screaming: Bright Yellow
                        pixels[pxIdx] = 255;
                        pixels[pxIdx + 1] = 230;
                        pixels[pxIdx + 2] = 0;
                    } else {
                        // Normal: SNN IP Pointer Blue
                        pixels[pxIdx] = 0;
                        pixels[pxIdx + 1] = 136;
                        pixels[pxIdx + 2] = 255;
                    }
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
    
    const brainStats = document.getElementById('brain-stats');
    const svgElement = d3.select('#brain-svg');
    svgElement.selectAll('*').remove();
    
    brainStats.innerHTML = "<p>Extracting Elite DNA from the Ark...</p>";
    
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        if (!data.elite) {
            brainStats.innerHTML = "<p style='color: var(--color-red);'>No Elite DNA currently alive.</p>";
            return;
        }
        
        const elite = data.elite;
        
        let html = `
            <div style="margin-bottom: 20px; display: flex; align-items: center; flex-wrap: wrap;">
                <span class="badge glow-cyan" title="Population of this exact DNA">ID: ${elite.id}</span>
                <span class="badge" title="Maximum age reached by this DNA" style="border-color: #00FF9D; color: #00FF9D;">Age: ${elite.age}</span>
                <span class="badge" title="Density" style="border-color: #B200FF; color: #B200FF;">Viscosity: ${elite.viscosity.toFixed(2)}</span>
            </div>
            <div style="font-family: monospace; font-size: 0.8rem; margin-bottom: 12px; color: #888;">
                DNA Hash: ${elite.genome_hex}...
            </div>
        `;
        brainStats.innerHTML = html;
        
        // Brain Visualization D3 Improvements
        const width = document.getElementById('brain-svg').clientWidth;
        const height = document.getElementById('brain-svg').clientHeight;
        
        const nodesMap = new Map();
        
        elite.synapses.forEach(s => {
            if (!nodesMap.has(s.source)) nodesMap.set(s.source, {id: s.source, type: s.source.startsWith('H') ? 'hidden' : 'input'});
            if (!nodesMap.has(s.target)) nodesMap.set(s.target, {id: s.target, type: s.target.startsWith('H') ? 'hidden' : 'output'});
        });
        
        const nodes = Array.from(nodesMap.values());
        const links = elite.synapses.map(s => ({
            source: s.source,
            target: s.target,
            weight: s.weight
        }));

        const getFriendlyName = (id) => {
            if (id.startsWith('In')) {
                const n = parseInt(id.replace('In ', ''));
                if (n < 4) return '👁 Vision ' + n;
                if (n >= 4 && n < 8) return '🔊 Audio ' + (n-4);
                if (n === 8) return '⚡ Energy';
                if (n === 9) return '🔥 Pain';
                return id;
            }
            if (id.startsWith('Out')) {
                const n = parseInt(id.replace('Out ', ''));
                if (n === 0) return '⬆ Fwd';
                if (n === 1) return '⬇ Bck';
                if (n === 2) return '⬅ Lft';
                if (n === 3) return '➡ Rgt';
                if (n === 4) return '🍽 Eat';
                if (n === 5) return '🧬 Repo';
                if (n === 6) return '🗣 Voice';
                return id;
            }
            return id; // Hidden nodes stay H n
        };
        
        // Define exact layered coordinates
        const inputNodes = nodes.filter(n => n.type === 'input').sort((a,b) => parseInt(a.id.split(' ')[1] || 0) - parseInt(b.id.split(' ')[1] || 0));
        const hiddenNodes = nodes.filter(n => n.type === 'hidden').sort((a,b) => parseInt(a.id.split(' ')[1] || 0) - parseInt(b.id.split(' ')[1] || 0));
        const outputNodes = nodes.filter(n => n.type === 'output').sort((a,b) => parseInt(a.id.split(' ')[1] || 0) - parseInt(b.id.split(' ')[1] || 0));

        inputNodes.forEach((n, i) => { n.fx = width * 0.15; n.fy = height * 0.1 + (i * ((height*0.8) / Math.max(1, inputNodes.length-1))); });
        hiddenNodes.forEach((n, i) => { n.fx = width * 0.5; n.fy = height * 0.1 + (i * ((height*0.8) / Math.max(1, hiddenNodes.length-1))); });
        outputNodes.forEach((n, i) => { n.fx = width * 0.85; n.fy = height * 0.1 + (i * ((height*0.8) / Math.max(1, outputNodes.length-1))); });

        svgElement.append('defs').selectAll('marker')
            .data(['end-excitatory', 'end-inhibitory'])
            .enter().append('marker')
            .attr('id', d => d)
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 22)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', d => d === 'end-excitatory' ? '#00FF9D' : '#FF0055');
            
        // gradients
        const defs = svgElement.select('defs');
        const gradIn = defs.append('radialGradient').attr('id', 'grad-input');
        gradIn.append('stop').attr('offset', '0%').attr('stop-color', '#00E5FF');
        gradIn.append('stop').attr('offset', '100%').attr('stop-color', '#007A99');
        
        const gradOut = defs.append('radialGradient').attr('id', 'grad-output');
        gradOut.append('stop').attr('offset', '0%').attr('stop-color', '#FF4E00');
        gradOut.append('stop').attr('offset', '100%').attr('stop-color', '#992E00');

        const gradHid = defs.append('radialGradient').attr('id', 'grad-hidden');
        gradHid.append('stop').attr('offset', '0%').attr('stop-color', '#D055FF');
        gradHid.append('stop').attr('offset', '100%').attr('stop-color', '#7A00B2');

        const g = svgElement.append('g');
        const zoom = d3.zoom().on('zoom', (event) => g.attr('transform', event.transform));
        svgElement.call(zoom);

        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(150))
            .force('collide', d3.forceCollide().radius(20));

        const link = g.append('g')
            .selectAll('line')
            .data(links)
            .enter().append('line')
            .attr('stroke', d => d.weight > 0 ? 'rgba(0,255,157,0.7)' : 'rgba(255,0,85,0.7)')
            .attr('stroke-width', d => Math.max(1.5, Math.min(8, Math.abs(d.weight))))
            .attr('marker-end', d => d.weight > 0 ? 'url(#end-excitatory)' : 'url(#end-inhibitory)')
            .style('filter', 'drop-shadow(0 0 3px rgba(255,255,255,0.3))');

        const node = g.append('g')
            .selectAll('circle')
            .data(nodes)
            .enter().append('circle')
            .attr('r', 12)
            .attr('fill', d => {
                if (d.type === 'input') return 'url(#grad-input)';
                if (d.type === 'output') return 'url(#grad-output)';
                return 'url(#grad-hidden)';
            })
            .attr('stroke', '#111')
            .attr('stroke-width', 2)
            .style('filter', 'drop-shadow(0 0 6px rgba(255,255,255,0.4))')
            .call(d3.drag()
                .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
                .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); })
            );

        const labels = g.append('g')
            .selectAll('text')
            .data(nodes)
            .enter().append('text')
            .text(d => getFriendlyName(d.id))
            .attr('font-size', '12px')
            .attr('font-family', 'var(--font-heading)')
            .attr('font-weight', 'bold')
            .attr('letter-spacing', '1px')
            .attr('fill', '#fff')
            .attr('dx', d => d.type === 'input' ? -15 : 15)
            .attr('dy', 4)
            .attr('text-anchor', d => d.type === 'input' ? 'end' : 'start')
            .style('text-shadow', '0 2px 4px rgba(0,0,0,0.8)');

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);
                
            labels
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });

        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            if (d.type === 'hidden') {
                d.fx = null;
                d.fy = null;
            }
        }
        
    } catch (err) {
        console.error(err);
        brainStats.innerHTML = `<p style='color: var(--color-red);'>Failed to fetch brain data: ${err.message}</p>`;
    }
});

btnClose.addEventListener('click', () => {
    modal.classList.add('hidden');
});

// Update every 100ms
setInterval(fetchState, 100);

// =========================================================================
// Terminal Logic
// =========================================================================
const termIn = document.getElementById('term-in');
const termOut = document.getElementById('term-out');

function printTerm(text, type='out') {
    const div = document.createElement('div');
    div.className = `term-line ${type}`;
    div.textContent = text;
    termOut.appendChild(div);
    termOut.scrollTop = termOut.scrollHeight;
}

let currentBroadcast = "";
let broadcastIndex = 0;
let broadcastInterval = null;

termIn.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
        const text = termIn.value;
        termIn.value = '';
        
        if (!text || text.toLowerCase() === 'stop') {
            // Stop broadcast
            currentBroadcast = "";
            if (broadcastInterval) clearInterval(broadcastInterval);
            printTerm(`> [SYS]: Broadcast stopped.`, 'sys');
            try {
                await fetch('/api/oracle', { method: 'POST', body: JSON.stringify({val: 0, target: -1}) });
            } catch(err) {}
            return;
        }

        printTerm(`> [USER]: ${text} (Broadcasting continuously...)`, 'in');
        currentBroadcast = text;
        broadcastIndex = 0;
        
        if (broadcastInterval) clearInterval(broadcastInterval);
        
        // Broadcast the string cyclically every 500ms
        broadcastInterval = setInterval(() => {
            if (currentBroadcast.length === 0) return;
            const charCode = currentBroadcast.charCodeAt(broadcastIndex);
            
            fetch('/api/oracle', {
                method: 'POST',
                body: JSON.stringify({val: charCode, target: -1})
            }).catch(err => {});
            
            broadcastIndex = (broadcastIndex + 1) % currentBroadcast.length;
        }, 500); 
    }
});

async function fetchTerminal() {
    try {
        const res = await fetch('/api/terminal');
        const data = await res.json();
        if (data.text) {
            printTerm(`> [ARK ELITE]: ${data.text}`, 'out');
        }
    } catch (err) {}
}

setInterval(fetchTerminal, 500);
