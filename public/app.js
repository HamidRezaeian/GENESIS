/* ═══════════════════════════════════════════════════════════
   GENESIS — Neuromorphic Observation Deck (app.js)
   Observer Mode: Real-time Telemetry & Neural Circuit Visualizer
   ═══════════════════════════════════════════════════════════ */

// ── Canvas Setup ──────────────────────────────────────────
const canvas = document.getElementById('ramCanvas');
const ctx = canvas.getContext('2d', { alpha: false });
canvas.width = 256;
canvas.height = 256;
let imgData = ctx.createImageData(256, 256);

// ── WebSocket Connection ─────────────────────────────────
let ws = null;
function connect() {
    const host = window.location.hostname || '127.0.0.1';
    ws = new WebSocket('ws://' + host + ':8085');
    
    ws.onopen = () => {
        const dot = document.getElementById('status-dot');
        if (dot) dot.style.background = '#10b981';
        ws.send(JSON.stringify({ type: 'set_auto_inject', enabled: true }));
        ws.send(JSON.stringify({ type: 'set_curriculum', enabled: true }));
    };
    
    ws.onclose = () => {
        const dot = document.getElementById('status-dot');
        if (dot) dot.style.background = '#ef4444';
        setTimeout(connect, 1500);
    };
    
    ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.type === 'state') onState(d);
        else if (d.type === 'status') onBrain(d);
        else if (d.type === 'library_list') onLibrary(d);
    };
}
connect();

// ── State Handler ─────────────────────────────────────────
let lastTick = 0, lastTime = performance.now();
let lastExtinctions = -1;

function onState(s) {
    // KPI updates
    const setTxt = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    
    setTxt('val-tick', s.tick ? s.tick.toLocaleString() : '0');
    if (document.getElementById('val-pop')) {
        document.getElementById('val-pop').innerHTML = (s.pop || 0).toLocaleString() + '<span class="dim">/' + (s.max_pop || 600) + '</span>';
    }
    setTxt('val-ext', s.extinctions !== undefined ? s.extinctions.toLocaleString() : '0');
    setTxt('val-elite-age', s.elite_age !== undefined ? s.elite_age.toLocaleString() : '0');
    setTxt('val-elite-iq', s.elite_iq !== undefined ? s.elite_iq + '%' : '0%');
    setTxt('val-agi-progress', s.agi_progress !== undefined ? s.agi_progress + '%' : '0%');
    setTxt('val-avg-age', s.avg_age !== undefined ? s.avg_age.toLocaleString() : '0');
    setTxt('val-refuges', s.num_refuge !== undefined ? s.num_refuge.toLocaleString() : '0');

    // Live cognition metrics
    if (s.metrics) {
        const m = s.metrics;
        setTxt('m-solve', m.solve_pct != null ? m.solve_pct.toFixed(0) + '%' : '—');
        setTxt('m-reads', m.reads || 0);
        setTxt('m-miss', m.miss || 0);
        setTxt('m-pred', m.pred || 0);
        setTxt('m-peer', m.peer || 0);
        setTxt('m-hact', m.hact != null ? m.hact.toFixed(2) : '—');
        setTxt('m-sensors', m.sensors || 0);
        setTxt('m-actuators', m.actuators || 0);
        setTxt('m-scratch', m.scratch || 0);
        if (s.universe_n !== undefined) setTxt('m-brainn', s.universe_n.toLocaleString());
    }

    // Engine Flags
    if (s.flags) applyFlags(s.flags);

    // Speed calculation
    const now = performance.now();
    if (s.tick > lastTick) {
        const dt = (now - lastTime) / 1000;
        if (dt > 0.5) {
            const speed = Math.round((s.tick - lastTick) / dt);
            setTxt('val-speed', speed.toLocaleString() + '/s');
            lastTick = s.tick;
            lastTime = now;
        }
    }

    // Autotelic Behavior Feed (Persian Synthesis)
    const behavEl = document.getElementById('behavior-text');
    if (behavEl) {
        let text = "";
        if (lastExtinctions !== -1 && s.extinctions > lastExtinctions) {
            text = "💥 <span class='text-crimson'>انقراض کلونی رخ داد!</span> نسل فعلی پاکسازی شد و نسل جدید متولد گردید.<br><br>";
        } else if (s.metrics && s.metrics.solve_pct !== undefined) {
            const pct = s.metrics.solve_pct;
            if (pct > 75) {
                text = "🧠 <span class='text-emerald'>ارگانیسم‌ها به پایداری شناختی رسیده‌اند!</span> پیش‌بینی دقیق توالی با موفقیت بالا انجام می‌شود.<br><br>";
            } else if (pct < 25) {
                text = "⚠️ <span class='text-amber'>ارگانیسم‌ها در فاز اکتشاف غیرایستا (REMAP) هستند.</span> انطباق درون-عمر STDP3C در حال بروزرسانی سیناپسی است.<br><br>";
            } else {
                text = "🔍 ارگانیسم‌ها در حال یادگیری تدریجی و حفظ نرخ انرژی مثبت تحت Footprint Economy هستند.<br><br>";
            }
        }
        
        if (s.elite_iq !== undefined) {
            let eliteDesc = `👑 <b>تحلیل ارگانیسم الیت (سن: ${s.elite_age} تیک | هوش: ${s.elite_iq}%)</b>: `;
            if (s.elite_iq > 70) {
                eliteDesc += "مدار عصبی الیت توانسته تغییرات الگوی محیطی را به صورت درون-عمر ردیابی و پیش‌بینی کند. ";
            } else {
                eliteDesc += "شبکه عصبی الیت در حال تنظیم وزن‌های سیناپسی برای دستیابی به انرژی خالص مثبت است. ";
            }

            if (s.metrics && s.metrics.hact !== undefined) {
                if (s.metrics.hact < 0.5) {
                    eliteDesc += "آنتروپی رفتاری پایین و هدفمند است.";
                } else {
                    eliteDesc += "رفتار حرکتی شامل کاوش محیطی و جستجوی فعال است.";
                }
            }
            text += eliteDesc;
        }
        behavEl.innerHTML = text;
    }
    lastExtinctions = s.extinctions;

    // RAM Canvas Render
    if (s.ram_b64 && imgData) {
        const bin = atob(s.ram_b64);
        const px = imgData.data;
        const len = bin.length;

        for (let i = 0; i < len; i++) {
            const v = bin.charCodeAt(i);
            const p = i << 2;
            let r = 7, g = 8, b = 14;

            if (v === 0x55) { r = 16; g = 185; b = 129; }       // Food (Emerald)
            else if (v === 0xAA) { r = 6; g = 182; b = 212; }   // Shelter (Cyan)
            else if (v >= 32 && v <= 126) { r = 139; g = 92; b = 246; } // Books (Purple)
            else if (v > 0) { r = 59; g = 130; b = 246; }      // Activity (Blue)

            px[p] = r; px[p+1] = g; px[p+2] = b; px[p+3] = 255;
        }

        // Draw Organisms
        if (s.org_positions) {
            for (let i = 0; i < s.org_positions.length; i++) {
                const pos = s.org_positions[i];
                const p = pos << 2;
                px[p] = 245; px[p+1] = 158; px[p+2] = 11; // Amber Organism Dot
            }
        }
        ctx.putImageData(imgData, 0, 0);
    }
}

function applyFlags(flags) {
    const bar = document.getElementById('flag-bar');
    if (!bar) return;
    bar.innerHTML = '';
    const activeFlags = ['FOOTPRINT_898', 'AUTO_REPRO_200k', 'REMAP_500', 'STDP3C_ON', 'MULTISCALE_25'];
    activeFlags.forEach(f => {
        const span = document.createElement('span');
        span.className = 'flag-chip active';
        span.textContent = f;
        bar.appendChild(span);
    });
}

// ── Neural Circuit Topology (D3.js) ────────────────────────
function onBrain(d) {
    if (!d.elite) return;
    const statsEl = document.getElementById('brain-stats');
    if (statsEl) {
        statsEl.innerHTML = `
            <div style="display: flex; gap: 16px; margin-bottom: 12px; font-family: var(--mono); font-size: 12px; flex-wrap: wrap;">
                <span>👑 <b>Elite Organism ID:</b> #${d.elite.id}</span>
                <span>⏳ <b>Age:</b> ${d.elite.age.toLocaleString()} Ticks</span>
                <span>🔬 <b>Viscosity:</b> ${d.elite.viscosity.toFixed(2)}</span>
                <span>🧬 <b>DNA Prefix:</b> <code style="color: var(--emerald);">${d.elite.genome_hex}...</code></span>
                <span>⚡ <b>Active Synapses:</b> ${d.elite.synapses ? d.elite.synapses.length : 0}</span>
            </div>
        `;
    }
    if (d.elite.synapses) {
        renderBrainSVG(d.elite.synapses);
    }
}

function renderBrainSVG(synapses) {
    const svg = d3.select('#brain-svg');
    svg.selectAll('*').remove();

    const wrapper = document.querySelector('.svg-wrapper');
    const width = wrapper ? wrapper.clientWidth : 800;
    const height = wrapper ? wrapper.clientHeight : 500;

    // Collect Nodes
    const nodeMap = new Map();
    synapses.forEach(s => {
        if (!nodeMap.has(s.source)) nodeMap.set(s.source, { id: s.source });
        if (!nodeMap.has(s.target)) nodeMap.set(s.target, { id: s.target });
    });

    const nodes = Array.from(nodeMap.values());
    const links = synapses.map(s => ({
        source: s.source,
        target: s.target,
        weight: s.weight
    }));

    // Layer Position Assignment (Inputs -> Hidden -> Outputs)
    const inNodes = nodes.filter(n => n.id.startsWith('In'));
    const outNodes = nodes.filter(n => n.id.startsWith('Out'));
    const hNodes = nodes.filter(n => !n.id.startsWith('In') && !n.id.startsWith('Out'));

    inNodes.forEach((n, i) => {
        n.x = 80;
        n.y = ((i + 1) * height) / (inNodes.length + 1);
    });
    outNodes.forEach((n, i) => {
        n.x = width - 80;
        n.y = ((i + 1) * height) / (outNodes.length + 1);
    });
    hNodes.forEach((n, i) => {
        n.x = width / 2 + (i % 2 === 0 ? -40 : 40);
        n.y = ((i + 1) * height) / (hNodes.length + 1);
    });

    const g = svg.append('g');

    // Draw Synaptic Links
    const linkGroup = g.append('g').selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('stroke', d => d.weight > 0 ? '#10b981' : '#ef4444')
        .attr('stroke-opacity', 0.7)
        .attr('stroke-width', d => Math.min(Math.abs(d.weight) * 0.8 + 1, 5))
        .attr('x1', d => nodeMap.get(d.source).x)
        .attr('y1', d => nodeMap.get(d.source).y)
        .attr('x2', d => nodeMap.get(d.target).x)
        .attr('y2', d => nodeMap.get(d.target).y);

    // Draw Neurons
    const nodeGroup = g.append('g').selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .attr('transform', d => `translate(${d.x}, ${d.y})`);

    nodeGroup.append('circle')
        .attr('r', 14)
        .attr('fill', d => {
            if (d.id.startsWith('In')) return '#10b981';
            if (d.id.startsWith('Out')) return '#06b6d4';
            return '#8b5cf6';
        })
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .style('filter', 'drop-shadow(0 0 6px rgba(139,92,246,0.5))');

    nodeGroup.append('text')
        .text(d => d.id)
        .attr('dy', 4)
        .attr('text-anchor', 'middle')
        .attr('fill', '#fff')
        .attr('font-size', '10px')
        .attr('font-family', 'var(--mono)')
        .attr('font-weight', '700');
}

// ── Oracle Broadcast Terminal ─────────────────────────────
const termIn = document.getElementById('term-in');
if (termIn) {
    termIn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && termIn.value.trim() && ws) {
            const text = termIn.value.trim();
            ws.send(JSON.stringify({ type: 'broadcast', text: text }));
            addTermLine('› ' + text, 't-sys');
            termIn.value = '';
        }
    });
}

function addTermLine(msg, cls = '') {
    const out = document.getElementById('term-out');
    if (!out) return;
    const div = document.createElement('div');
    div.className = 't-line ' + cls;
    div.textContent = msg;
    out.appendChild(div);
    if (out.childNodes.length > 150) out.removeChild(out.firstChild);
    out.scrollTop = out.scrollHeight;
}

// ── Brain Modal ───────────────────────────────────────────
const btnBrain = document.getElementById('btn-brain');
const modal = document.getElementById('brain-modal');
const btnClose = document.getElementById('btn-close-modal');

if (btnBrain && modal) {
    btnBrain.addEventListener('click', () => {
        modal.classList.remove('hidden');
        if (ws) ws.send(JSON.stringify({ type: 'get_brain' }));
    });
}
if (btnClose && modal) {
    btnClose.addEventListener('click', () => modal.classList.add('hidden'));
}
