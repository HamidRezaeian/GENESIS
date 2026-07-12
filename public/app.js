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

let ws = null;
function initWebSocket() {
    const hostname = window.location.hostname || '127.0.0.1';
    ws = new WebSocket('ws://' + hostname + ':8085');
    ws.onopen = () => {
        ws.send(JSON.stringify({type: 'get_library'}));
        const val = parseInt(document.getElementById('energy-rate-slider').value);
        ws.send(JSON.stringify({ type: 'set_energy_rate', rate: val / 1000 }));
    };
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'state') {
            handleState(data);
            const hideFails = document.getElementById('filter-success').checked;
            
            if (data.terminal) {
                const line = printTerm(`> [ARK ELITE]: ${data.terminal}`, 'out');
                line.classList.add('log-fail');
                if (hideFails) line.style.display = 'none';
            }
            if (data.read_events) {
                data.read_events.forEach(ev => {
                    if (ev.type === 'success') {
                        printTerm(`> [CURRICULUM] Org #${ev.org} absorbed knowledge: '${ev.char}'`, 'sys');
                    } else if (ev.type === 'fail') {
                        const line = printTerm(`> [CURRICULUM] Org #${ev.org} failed at '${ev.target}' (guessed '${ev.guess}')`, 'in');
                        line.classList.add('log-fail');
                        if (hideFails) line.style.display = 'none';
                    }
                });
            }
        } else if (data.type === 'status') {
            handleBrainStatus(data);
        } else if (data.type === 'library_list') {
            const select = document.getElementById('library-select');
            select.innerHTML = '<option value="">-- Select Curriculum --</option>';
            for (const category in data.books) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = category;
                data.books[category].forEach(book => {
                    const opt = document.createElement('option');
                    opt.value = `${category}|${book}`;
                    opt.textContent = book;
                    optgroup.appendChild(opt);
                });
                select.appendChild(optgroup);
            }
        }
    };
    ws.onclose = () => {
        setTimeout(initWebSocket, 1000);
    };
}
initWebSocket();

function handleState(state) {
    try {

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
                let pType = null;

                if (val === 0x55) {
                    // Energy: Green
                    pType = 'energy';
                    r = 0; g = 255; b = 157;
                } else if (val === 0xFF) {
                    // Trap: Red
                    pType = 'trap';
                    r = 255; g = 0; b = 85;
                } else if (val >= 32 && val <= 126) {
                    // Curriculum Text: Purple
                    pType = 'book';
                    r = 168; g = 85; b = 247;
                }

                if (window.highlightFilter && window.highlightFilter !== pType && r !== 10) {
                    r = Math.floor(r * 0.15);
                    g = Math.floor(g * 0.15);
                    b = Math.floor(b * 0.15);
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
                    const isScreaming = screamingOrgs.has(pos);
                    const pType = isScreaming ? 'voice' : 'ip';
                    
                    let r, g, b;
                    if (isScreaming) {
                        // Screaming: Bright Yellow
                        r = 255; g = 230; b = 0;
                    } else {
                        // Normal: SNN IP Pointer Blue
                        r = 0; g = 136; b = 255;
                    }

                    if (window.highlightFilter && window.highlightFilter !== pType) {
                        r = Math.floor(r * 0.15);
                        g = Math.floor(g * 0.15);
                        b = Math.floor(b * 0.15);
                    }

                    pixels[pxIdx] = r;
                    pixels[pxIdx + 1] = g;
                    pixels[pxIdx + 2] = b;
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
const btnFullscreen = document.getElementById('btn-fullscreen');
const mainViz = document.getElementById('main-viz');
const liveBrainWrapper = document.getElementById('wrapper-live-brain');
const modal = document.getElementById('brain-modal');
const btnClose = document.getElementById('btn-close-modal');
const brainData = document.getElementById('brain-data');

let liveBrainInterval = null;

if (btnFullscreen) {
    btnFullscreen.addEventListener('click', () => {
        mainViz.classList.toggle('fullscreen-mode');
        if (mainViz.classList.contains('fullscreen-mode')) {
            btnFullscreen.innerText = 'EXIT FULL SCREEN';
            liveBrainWrapper.style.display = 'flex';
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({type: 'get_status'}));
            liveBrainInterval = setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN && mainViz.classList.contains('fullscreen-mode')) {
                    ws.send(JSON.stringify({type: 'get_status'}));
                }
            }, 2000);
        } else {
            btnFullscreen.innerText = 'FULL SCREEN';
            liveBrainWrapper.style.display = 'none';
            if (liveBrainInterval) {
                clearInterval(liveBrainInterval);
                liveBrainInterval = null;
            }
        }
    });
}

btnAnalyze.addEventListener('click', () => {
    modal.classList.remove('hidden');
    
    const brainStats = document.getElementById('brain-stats');
    const svgElement = d3.select('#brain-svg');
    svgElement.selectAll('*').remove();
    
    brainStats.innerHTML = "<p>Extracting Elite DNA from the Ark...</p>";
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type: 'get_status'}));
    } else {
        brainStats.innerHTML = "<p style='color: var(--color-red);'>WebSocket not connected.</p>";
    }
});

function handleBrainStatus(data) {
    const isLive = document.getElementById('main-viz').classList.contains('fullscreen-mode');
    const prefix = isLive ? 'live-brain' : 'brain';
    const brainStats = document.getElementById(prefix + '-stats');
    const svgElement = d3.select('#' + prefix + '-svg');
    try {
        if (!data.elite) {
            brainStats.innerHTML = "<p style='color: var(--color-red);'>No Elite DNA currently alive.</p>";
            return;
        }
        
        const elite = data.elite;
        
        // Prevent re-rendering if it's the exact same genome (avoids D3 graph bouncing)
        if (window.lastRenderedEliteHex === elite.genome_hex && isLive) {
            return;
        }
        window.lastRenderedEliteHex = elite.genome_hex;
        
        // Clear before rendering
        svgElement.selectAll('*').remove();
        
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
        // Use a fixed internal coordinate system for perfect scaling
        const width = 1200;
        const height = 800;
        svgElement.attr('viewBox', `0 0 ${width} ${height}`);
        svgElement.attr('preserveAspectRatio', 'xMidYMid meet');
        
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

        // Labels mirror the real sensor/motor map in neuromorphic_engine.py:
        //   Inputs (15): 0 Energy, 1 Bias, 2 Crowding, 3 RAM byte, 4-6 neighbour Voice bits,
        //                7-14 Oracle broadcast bits.
        //   Outputs (14): 0 Jmp+1, 1 Jmp-1, 2 Jmp+10, 3 Jmp-10, 4 Consume, 5 Reproduce,
        //                6-13 Vocal-cord bits.
        const getFriendlyName = (id) => {
            if (id.startsWith('In')) {
                const n = parseInt(id.replace('In ', ''));
                if (n === 0) return '⚡ Energy';
                if (n === 1) return '• Bias';
                if (n === 2) return '🌡 Crowding';
                if (n === 3) return '👁 RAM Byte';
                if (n === 4) return '🔊 Voice-Lo';
                if (n === 5) return '🔊 Voice-Mid';
                if (n === 6) return '🔊 Voice-Hi';
                if (n >= 7 && n <= 14) return '📡 Oracle b' + (n-7);
                if (n >= 15 && n <= 22) return '👁 Eye b' + (n-15);
                if (n === 23) return '🧭 Food Fwd';
                if (n === 24) return '🧭 Food Bck';
                return id;
            }
            if (id.startsWith('Out')) {
                const n = parseInt(id.replace('Out ', ''));
                if (n === 0) return '⬆ Jmp+1';
                if (n === 1) return '⬇ Jmp-1';
                if (n === 2) return '⏫ Jmp+10';
                if (n === 3) return '⏬ Jmp-10';
                if (n === 4) return '🍽 Eat';
                if (n === 5) return '🧬 Repro';
                if (n >= 6 && n <= 13) return '🗣 Voice b' + (n-6);
                return id;
            }
            return id; // Hidden nodes stay H n
        };

        const getNodeDescription = (id) => {
            if (id.startsWith('In')) {
                const n = parseInt(id.replace('In ', ''));
                if (n === 0) return 'Senses the organism’s own internal energy (ATP) reserve, normalised to 0..1.';
                if (n === 1) return 'Constant bias input (always 0.5). Lets the network learn a fixed offset.';
                if (n === 2) return 'Local crowding: how densely packed the surrounding RAM is with other organisms. Drives dispersal/migration.';
                if (n === 3) return 'The raw value of the RAM byte the organism’s pointer is currently sitting on, normalised to 0..1.';
                if (n >= 4 && n <= 6) return 'Auditory channel: OR-combined vocal-cord bits emitted by the immediate left/right neighbours (low/mid/high group).';
                if (n >= 7 && n <= 14) return 'Oracle uplink: bit ' + (n-7) + ' of the 8-bit character currently broadcast into the universe by the user terminal.';
                if (n >= 15 && n <= 22) return 'Reading eye: bit ' + (n-15) + ' of the RAM byte under the pointer.';
                if (n === 23) return 'Food Ahead: density of free energy (0x55) in the forward path.';
                if (n === 24) return 'Food Behind: density of free energy (0x55) in the backward path.';
                return 'Sensory input from the environment.';
            }
            if (id.startsWith('Out')) {
                const n = parseInt(id.replace('Out ', ''));
                if (n === 0) return 'Motor command: move the instruction pointer +1 byte along the RAM ring.';
                if (n === 1) return 'Motor command: move the instruction pointer -1 byte along the RAM ring.';
                if (n === 2) return 'Motor command: jump the instruction pointer +10 bytes (fast forward).';
                if (n === 3) return 'Motor command: jump the instruction pointer -10 bytes (fast reverse).';
                if (n === 4) return 'Consume the food byte (0x55) under the pointer, converting it to ATP.';
                if (n === 5) return 'Initiate reproduction: pay the genome copy cost and split remaining energy with the child.';
                if (n >= 6 && n <= 13) return 'Vocal-cord motor bit ' + (n-6) + '. The 8 voice bits together form the ASCII character the organism emits.';
                return 'Motor output command.';
            }
            if (id.startsWith('H')) {
                return 'Hidden interneuron. Processes information between inputs and outputs, acting as logic gates or memory circuits.';
            }
            return 'Unknown neural structure.';
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
            
        // gradients and filters
        const defs = svgElement.select('defs');
        const gradIn = defs.append('radialGradient').attr('id', 'grad-input');
        gradIn.append('stop').attr('offset', '0%').attr('stop-color', 'hsl(186, 100%, 50%)');
        gradIn.append('stop').attr('offset', '100%').attr('stop-color', 'hsl(186, 100%, 20%)');
        
        const gradOut = defs.append('radialGradient').attr('id', 'grad-output');
        gradOut.append('stop').attr('offset', '0%').attr('stop-color', 'hsl(18, 100%, 50%)');
        gradOut.append('stop').attr('offset', '100%').attr('stop-color', 'hsl(18, 100%, 20%)');

        const gradHid = defs.append('radialGradient').attr('id', 'grad-hidden');
        gradHid.append('stop').attr('offset', '0%').attr('stop-color', 'hsl(276, 100%, 50%)');
        gradHid.append('stop').attr('offset', '100%').attr('stop-color', 'hsl(276, 100%, 20%)');

        function createGlow(id) {
            const filter = defs.append('filter')
                .attr('id', id)
                .attr('x', '-50%').attr('y', '-50%')
                .attr('width', '200%').attr('height', '200%');
            filter.append('feGaussianBlur')
                .attr('stdDeviation', '3')
                .attr('result', 'coloredBlur');
            const feMerge = filter.append('feMerge');
            feMerge.append('feMergeNode').attr('in', 'coloredBlur');
            feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
        }
        createGlow('glow-input');
        createGlow('glow-output');
        createGlow('glow-hidden');
        createGlow('glow-excitatory');
        createGlow('glow-inhibitory');

        const g = svgElement.append('g');
        const zoom = d3.zoom()
            .scaleExtent([0.5, 3])
            .on('zoom', (event) => g.attr('transform', event.transform));
        
        svgElement.call(zoom)
            .on("dblclick.zoom", null)
            .on("wheel.zoom", null);

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
            .attr('filter', d => d.weight > 0 ? 'url(#glow-excitatory)' : 'url(#glow-inhibitory)')
            .style('cursor', 'pointer')
            .on('click', (e, d) => showInfo(`<b>SYNAPSE</b><br/>From: ${getFriendlyName(d.source.id || d.source)}<br/>To: ${getFriendlyName(d.target.id || d.target)}<br/>Weight: <span style="color:${d.weight > 0 ? '#00FF9D' : '#FF0055'}">${d.weight.toFixed(4)}</span><br/><br/><span style="color:#aaa; font-size: 0.9em; max-width: 250px; display:inline-block;">${d.weight > 0 ? 'Excitatory: Increases the probability of the target node firing.' : 'Inhibitory: Suppresses the probability of the target node firing.'}</span>`));

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
            .attr('filter', d => {
                if (d.type === 'input') return 'url(#glow-input)';
                if (d.type === 'output') return 'url(#glow-output)';
                return 'url(#glow-hidden)';
            })
            .style('cursor', 'pointer')
            .on('click', (e, d) => showInfo(`<b>NODE: ${getFriendlyName(d.id)}</b><br/>Layer: ${d.type.toUpperCase()}<br/>ID: ${d.id}<br/><br/><span style="color:#aaa; font-size: 0.9em; max-width: 250px; display:inline-block; line-height: 1.4;">${getNodeDescription(d.id)}</span>`))
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended)
            );

        const labels = g.append('g')
            .selectAll('text')
            .data(nodes)
            .enter().append('text')
            .text(d => getFriendlyName(d.id))
            .attr('font-size', '14px')
            .attr('font-family', 'var(--font-heading)')
            .attr('font-weight', 'bold')
            .attr('letter-spacing', '1px')
            .attr('fill', '#fff')
            .attr('dx', d => d.type === 'input' ? -15 : 15)
            .attr('dy', 4)
            .attr('text-anchor', d => d.type === 'input' ? 'end' : 'start')
            .style('text-shadow', '0 2px 4px rgba(0,0,0,0.8)')
            .style('pointer-events', 'none');
            
        function showInfo(htmlContent) {
            let panel = document.getElementById('d3-info-panel');
            if (!panel) {
                panel = document.createElement('div');
                panel.id = 'd3-info-panel';
                panel.style.position = 'absolute';
                panel.style.bottom = '20px';
                panel.style.right = '20px';
                panel.style.background = 'rgba(10,20,30,0.9)';
                panel.style.border = '1px solid var(--color-cyan)';
                panel.style.padding = '12px';
                panel.style.borderRadius = '6px';
                panel.style.color = '#fff';
                panel.style.fontFamily = 'monospace';
                panel.style.pointerEvents = 'none';
                panel.style.boxShadow = '0 0 15px rgba(0,255,157,0.2)';
                document.getElementById('brain-data').appendChild(panel);
            }
            panel.innerHTML = htmlContent;
        }

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
        brainStats.innerHTML = `<p style='color: var(--color-red);'>Failed to parse brain data: ${err.message}</p>`;
    }
}

btnClose.addEventListener('click', () => {
    modal.classList.add('hidden');
});

// Removed setInterval polling

// =========================================================================
// Oracle Terminal & Injections & Environment
// =========================================================================

const energyRateSlider = document.getElementById('energy-rate-slider');
const energyRateVal = document.getElementById('energy-rate-val');
energyRateSlider.addEventListener('input', (e) => {
    const val = parseInt(e.target.value);
    const percentage = (val / 10).toFixed(1);
    energyRateVal.textContent = `${percentage}%`;
    const prob = val / 1000;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_energy_rate', rate: prob }));
    }
});
energyRateSlider.addEventListener('change', (e) => {
    const val = parseInt(e.target.value);
    const prob = val / 1000;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_energy_rate', rate: prob }));
        printTerm(`> [SYS]: Environmental energy generation rate shifted to ${(prob*100).toFixed(1)}%`, 'sys');
    }
});

const termIn = document.getElementById('term-in');
const termOut = document.getElementById('term-out');

function printTerm(text, type='out') {
    const div = document.createElement('div');
    div.className = `term-line ${type}`;
    div.textContent = text;
    termOut.appendChild(div);
    
    // Limit to 200 lines to prevent DOM bloat and UI freezing
    while (termOut.children.length > 200) {
        termOut.removeChild(termOut.firstChild);
    }
    
    termOut.scrollTop = termOut.scrollHeight;
    return div;
}

document.getElementById('filter-success').addEventListener('change', (e) => {
    const hide = e.target.checked;
    document.querySelectorAll('.log-fail').forEach(el => {
        el.style.display = hide ? 'none' : 'block';
    });
    termOut.scrollTop = termOut.scrollHeight;
});

let currentBroadcast = "";
let broadcastIndex = 0;
let broadcastInterval = null;

// removed redundant listener

// =========================================================================
// Legend Hover/Click Highlighting
// =========================================================================

window.highlightFilter = null;
const setHighlight = (type) => {
    window.highlightFilter = type;
    document.getElementById('ramCanvas').style.opacity = '0.9'; // minor visual feedback
};
const clearHighlight = () => {
    window.highlightFilter = null;
    document.getElementById('ramCanvas').style.opacity = '1';
};

['leg-energy', 'leg-trap', 'leg-ip', 'leg-voice', 'leg-book'].forEach(id => {
    const el = document.getElementById(id);
    if(el) {
        const type = id.replace('leg-', '');
        
        // Mouse events
        el.addEventListener('mousedown', () => setHighlight(type));
        el.addEventListener('mouseup', clearHighlight);
        el.addEventListener('mouseleave', clearHighlight);
        
        // Touch events for mobile/tablet
        el.addEventListener('touchstart', (e) => { e.preventDefault(); setHighlight(type); }, {passive: false});
        el.addEventListener('touchend', (e) => { e.preventDefault(); clearHighlight(); }, {passive: false});
        el.addEventListener('touchcancel', clearHighlight);
    }
});    

termIn.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
        const text = termIn.value;
        termIn.value = '';
        
        if (!text || text.toLowerCase() === 'stop') {
            // Stop broadcast
            currentBroadcast = "";
            if (broadcastInterval) clearInterval(broadcastInterval);
            printTerm(`> [SYS]: Broadcast stopped.`, 'sys');
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'oracle', val: 0, target: -1}));
            }
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
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'oracle', val: charCode, target: -1}));
            }
            
            broadcastIndex = (broadcastIndex + 1) % currentBroadcast.length;
        }, 500); 
    }
});
// =========================================================================
// Library of Genesis Logic
// =========================================================================
document.getElementById('btn-inject-lib').addEventListener('click', () => {
    const select = document.getElementById('library-select');
    if (!select.value) return;
    const parts = select.value.split('|');
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'inject_curriculum_file',
            category: parts[0],
            book_name: parts[1]
        }));
        printTerm(`> [SYS]: Injected curriculum: [${parts[0]}] ${parts[1]}`, 'sys');
    }
});

document.getElementById('btn-inject-custom').addEventListener('click', () => {
    const input = document.getElementById('custom-book-input');
    if (!input.value) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'inject_custom_book',
            text: input.value
        }));
        printTerm(`> [SYS]: Injected custom knowledge: "${input.value}"`, 'sys');
        input.value = '';
    }
});

