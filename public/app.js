/* ═══════════════════════════════════════════════════════════
   GENESIS — Observation Deck (app.js)
   Lightweight: no framework, requestAnimationFrame gated,
   DOM writes batched, terminal capped at 150 lines.
   ═══════════════════════════════════════════════════════════ */

// ── Canvas Setup ──────────────────────────────────────────
const canvas = document.getElementById('ramCanvas');
const ctx = canvas.getContext('2d', { alpha: false });
canvas.width = 256;
canvas.height = 256;
let imgData = ctx.createImageData(256, 256);

// ── Chart ─────────────────────────────────────────────────
let chart = null;
function initChart() {
    const c = document.getElementById('extinctionChart').getContext('2d');
    chart = new Chart(c, {
        type: 'line',
        data: { labels: [], datasets: [{
            label: 'Era Lifespan',
            data: [],
            borderColor: '#f43f5e',
            backgroundColor: 'rgba(244,63,94,0.08)',
            borderWidth: 1.5,
            pointRadius: 0,
            fill: true,
            tension: 0.3
        }]},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: { display: false },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
                    ticks: { color: '#555', font: { size: 9 }, callback: v => (v/1000).toFixed(0)+'k' }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}
initChart();

// ── WebSocket ─────────────────────────────────────────────
let ws = null;
function connect() {
    const host = window.location.hostname || '127.0.0.1';
    ws = new WebSocket('ws://' + host + ':8085');
    ws.onopen = () => {
        document.getElementById('status-dot').style.background = '#34d399';
        ws.send(JSON.stringify({ type: 'get_library' }));
        const v = parseInt(document.getElementById('energy-rate-slider').value);
        ws.send(JSON.stringify({ type: 'set_energy_rate', rate: v / 1000 }));
    };
    ws.onclose = () => {
        document.getElementById('status-dot').style.background = '#f43f5e';
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
const hideFails = () => document.getElementById('filter-success').checked;

function onState(s) {
    // KPI updates (cheap DOM writes)
    document.getElementById('val-tick').textContent = s.tick.toLocaleString();
    document.getElementById('val-pop').innerHTML = s.pop.toLocaleString() + '<span class="dim">/' + s.max_pop + '</span>';
    document.getElementById('val-ext').textContent = s.extinctions.toLocaleString();
    if (s.elite_age !== undefined) document.getElementById('val-elite-age').textContent = s.elite_age.toLocaleString();
    if (s.elite_iq !== undefined) document.getElementById('val-elite-iq').textContent = s.elite_iq + '%';
    if (s.avg_age !== undefined) document.getElementById('val-avg-age').textContent = s.avg_age.toLocaleString();
    if (s.num_refuge !== undefined) document.getElementById('val-refuges').textContent = s.num_refuge.toLocaleString();

    // Speed calc
    const now = performance.now();
    if (s.tick > lastTick) {
        const dt = (now - lastTime) / 1000;
        if (dt > 0.5) {
            const speed = Math.round((s.tick - lastTick) / dt);
            document.getElementById('val-speed').textContent = speed.toLocaleString() + '/s';
            lastTick = s.tick;
            lastTime = now;
        }
    }

    // Chart
    if (chart && s.ext_history) {
        chart.data.labels = s.ext_history.map(h => '');
        chart.data.datasets[0].data = s.ext_history.map(h => h.rate);
        chart.update();
    }

    // RAM Canvas
    if (s.ram_b64 && imgData) {
        const bin = atob(s.ram_b64);
        const px = imgData.data;
        const len = bin.length;

        for (let i = 0; i < len; i++) {
            const v = bin.charCodeAt(i);
            const p = i << 2;
            let r = 8, g = 8, b = 12;

            if (v === 0x55) { r = 52; g = 211; b = 153; }
            else if (v === 0xFF) { r = 244; g = 63; b = 94; }
            else if (v >= 32 && v <= 126) { r = 167; g = 139; b = 250; }

            if (window._hl && window._hl !== (v === 0x55 ? 'energy' : v === 0xFF ? 'trap' : v >= 32 && v <= 126 ? 'book' : null)) {
                r = r >> 3; g = g >> 3; b = b >> 3;
            }

            px[p] = r; px[p+1] = g; px[p+2] = b; px[p+3] = 255;
        }

        // Organisms
        const orgs = s.orgs;
        const screaming = new Set(s.screaming_orgs || []);
        for (let i = 0; i < orgs.length; i++) {
            const pos = orgs[i];
            if (pos >= 0 && pos < len) {
                const p = pos << 2;
                const sc = screaming.has(pos);
                const type = sc ? 'voice' : 'ip';
                let r, g, b;
                if (sc) { r = 250; g = 204; b = 21; }
                else { r = 96; g = 165; b = 250; }
                if (window._hl && window._hl !== type) { r >>= 3; g >>= 3; b >>= 3; }
                px[p] = r; px[p+1] = g; px[p+2] = b;
            }
        }
        ctx.putImageData(imgData, 0, 0);
    }

    // Terminal events
    if (s.terminal) {
        const el = tprint('› [ELITE]: ' + s.terminal, 't-out');
        el.classList.add('log-fail');
        if (hideFails()) el.style.display = 'none';
    }
    if (s.read_events) {
        s.read_events.forEach(ev => {
            if (ev.type === 'success') {
                tprint('› Org #' + ev.org + " read '" + ev.char + "'", 't-sys');
            } else if (ev.type === 'fail') {
                const el = tprint('› Org #' + ev.org + " missed '" + ev.target + "' (guessed '" + ev.guess + "')", 't-in');
                el.classList.add('log-fail');
                if (hideFails()) el.style.display = 'none';
            } else if (ev.type === 'predict') {
                tprint('› Org #' + ev.org + " predicted '" + ev.char + "' ★", 't-out');
            }
        });
    }
}

// ── Terminal ──────────────────────────────────────────────
const termOut = document.getElementById('term-out');
function tprint(text, cls = 't-out') {
    const d = document.createElement('div');
    d.className = 't-line ' + cls;
    d.textContent = text;
    termOut.appendChild(d);
    while (termOut.children.length > 150) termOut.removeChild(termOut.firstChild);
    termOut.scrollTop = termOut.scrollHeight;
    return d;
}

// ── Library ───────────────────────────────────────────────
function onLibrary(d) {
    const sel = document.getElementById('library-select');
    sel.innerHTML = '<option value="">— Select Curriculum —</option>';
    for (const cat in d.books) {
        const og = document.createElement('optgroup');
        og.label = cat;
        d.books[cat].forEach(b => {
            const o = document.createElement('option');
            o.value = cat + '|' + b;
            o.textContent = b;
            og.appendChild(o);
        });
        sel.appendChild(og);
    }
}

// ── Brain Analyzer ───────────────────────────────────────
const modal = document.getElementById('brain-modal');

document.getElementById('btn-brain').addEventListener('click', () => {
    modal.classList.remove('hidden');
    document.getElementById('brain-stats').innerHTML = '<p class="dim">Extracting Elite DNA…</p>';
    d3.select('#brain-svg').selectAll('*').remove();
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'get_status' }));
});

document.getElementById('btn-close-modal').addEventListener('click', () => {
    modal.classList.add('hidden');
});

let lastEliteHex = '';
function onBrain(data) {
    const stats = document.getElementById('brain-stats');
    const svg = d3.select('#brain-svg');

    if (!data.elite) {
        stats.innerHTML = '<p style="color:var(--red)">No Elite DNA alive.</p>';
        return;
    }
    const e = data.elite;
    if (lastEliteHex === e.genome_hex) return;
    lastEliteHex = e.genome_hex;

    svg.selectAll('*').remove();
    stats.innerHTML =
        '<span class="badge badge-accent">ID: ' + e.id + '</span>' +
        '<span class="badge">Age: ' + e.age + '</span>' +
        '<span class="badge badge-purple">Viscosity: ' + e.viscosity.toFixed(2) + '</span>';

    // Build graph
    const W = 1200, H = 800;
    svg.attr('viewBox', '0 0 ' + W + ' ' + H).attr('preserveAspectRatio', 'xMidYMid meet');

    const nodeMap = new Map();
    e.synapses.forEach(s => {
        if (!nodeMap.has(s.source)) nodeMap.set(s.source, { id: s.source, type: s.source.startsWith('H') ? 'hidden' : 'input' });
        if (!nodeMap.has(s.target)) nodeMap.set(s.target, { id: s.target, type: s.target.startsWith('H') ? 'hidden' : 'output' });
    });
    const nodes = Array.from(nodeMap.values());
    const links = e.synapses.map(s => ({ source: s.source, target: s.target, weight: s.weight }));

    const nameMap = {
        'In 0': '⚡ Energy', 'In 1': '• Bias', 'In 2': '🌡 Crowd', 'In 3': '👁 RAM',
        'In 4': '♪ VoLo', 'In 5': '♪ VoMid', 'In 6': '♪ VoHi',
        'Out 0': '→ +1', 'Out 1': '← −1', 'Out 2': '⇒ +10', 'Out 3': '⇐ −10',
        'Out 4': '🍽 Eat', 'Out 5': '🧬 Repro'
    };
    for (let i = 7; i <= 14; i++) nameMap['In ' + i] = '📡 Orc b' + (i-7);
    for (let i = 15; i <= 22; i++) nameMap['In ' + i] = '👁 Eye b' + (i-15);
    nameMap['In 23'] = '🧭 FwdFood';
    nameMap['In 24'] = '🧭 BckFood';
    for (let i = 6; i <= 13; i++) nameMap['Out ' + i] = '🗣 Voice b' + (i-6);
    const name = id => nameMap[id] || id;

    // Layout
    const inp = nodes.filter(n => n.type === 'input').sort((a,b) => parseInt(a.id.split(' ')[1]||0) - parseInt(b.id.split(' ')[1]||0));
    const hid = nodes.filter(n => n.type === 'hidden').sort((a,b) => parseInt(a.id.split(' ')[1]||0) - parseInt(b.id.split(' ')[1]||0));
    const out = nodes.filter(n => n.type === 'output').sort((a,b) => parseInt(a.id.split(' ')[1]||0) - parseInt(b.id.split(' ')[1]||0));

    const space = (arr, x) => arr.forEach((n,i) => { n.fx = W*x; n.fy = H*0.08 + i*((H*0.84)/Math.max(1,arr.length-1)); });
    space(inp, 0.12);
    space(hid, 0.5);
    space(out, 0.88);

    // Defs
    const defs = svg.append('defs');
    ['exc','inh'].forEach(t => {
        defs.append('marker').attr('id','arr-'+t)
            .attr('viewBox','0 -4 8 8').attr('refX',18).attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
            .append('path').attr('d','M0,-4L8,0L0,4').attr('fill', t==='exc'?'#34d399':'#f43f5e');
    });

    const g = svg.append('g');
    svg.call(d3.zoom().scaleExtent([0.3,3]).on('zoom', ev => g.attr('transform', ev.transform)));

    const sim = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(120))
        .force('collide', d3.forceCollide(16));

    const linkEl = g.append('g').selectAll('line').data(links).enter().append('line')
        .attr('stroke', d => d.weight > 0 ? 'rgba(52,211,153,0.5)' : 'rgba(244,63,94,0.5)')
        .attr('stroke-width', d => Math.max(1, Math.min(5, Math.abs(d.weight) * 0.8)))
        .attr('marker-end', d => d.weight > 0 ? 'url(#arr-exc)' : 'url(#arr-inh)');

    const colors = { input: '#60a5fa', hidden: '#a78bfa', output: '#fb923c' };
    const nodeEl = g.append('g').selectAll('circle').data(nodes).enter().append('circle')
        .attr('r', 8)
        .attr('fill', d => colors[d.type])
        .attr('stroke', '#0a0a0f')
        .attr('stroke-width', 1.5)
        .style('cursor', 'pointer')
        .call(d3.drag()
            .on('start', (ev,d) => { if(!ev.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
            .on('drag', (ev,d) => { d.fx=ev.x; d.fy=ev.y; })
            .on('end', (ev,d) => { if(!ev.active) sim.alphaTarget(0); if(d.type==='hidden'){d.fx=null;d.fy=null;} })
        );

    const labelEl = g.append('g').selectAll('text').data(nodes).enter().append('text')
        .text(d => name(d.id))
        .attr('font-size', '11px').attr('font-family', 'Inter, sans-serif').attr('fill', '#aaa')
        .attr('dx', d => d.type === 'input' ? -12 : 12).attr('dy', 3)
        .attr('text-anchor', d => d.type === 'input' ? 'end' : 'start')
        .style('pointer-events', 'none');

    sim.on('tick', () => {
        linkEl.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
        nodeEl.attr('cx',d=>d.x).attr('cy',d=>d.y);
        labelEl.attr('x',d=>d.x).attr('y',d=>d.y);
    });
}

// ── Fullscreen ────────────────────────────────────────────
const ramSection = document.getElementById('ram-section');
document.getElementById('btn-fullscreen').addEventListener('click', () => {
    ramSection.classList.toggle('fullscreen');
    const btn = document.getElementById('btn-fullscreen');
    btn.textContent = ramSection.classList.contains('fullscreen') ? 'Exit' : 'Expand';
});

// ── Legend Filter ─────────────────────────────────────────
window._hl = null;
document.querySelectorAll('.legend-item').forEach(el => {
    const type = el.dataset.type;
    el.addEventListener('mousedown', () => { window._hl = type; });
    el.addEventListener('mouseup', () => { window._hl = null; });
    el.addEventListener('mouseleave', () => { window._hl = null; });
    el.addEventListener('touchstart', e => { e.preventDefault(); window._hl = type; }, { passive: false });
    el.addEventListener('touchend', e => { e.preventDefault(); window._hl = null; }, { passive: false });
});

// ── Energy Slider ─────────────────────────────────────────
const slider = document.getElementById('energy-rate-slider');
const sliderVal = document.getElementById('energy-rate-val');
slider.addEventListener('input', () => {
    const v = parseInt(slider.value);
    sliderVal.textContent = (v/10).toFixed(1) + '%';
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'set_energy_rate', rate: v/1000 }));
});

// ── Oracle Terminal Input ────────────────────────────────
let broadcast = '', bcastIdx = 0, bcastTimer = null;
document.getElementById('term-in').addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const text = e.target.value.trim();
    e.target.value = '';
    if (!text || text.toLowerCase() === 'stop') {
        broadcast = '';
        if (bcastTimer) clearInterval(bcastTimer);
        tprint('› Broadcast stopped.', 't-sys');
        if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'oracle', val: 0, target: -1 }));
        return;
    }
    tprint('› [USER]: ' + text + ' (broadcasting…)', 't-in');
    broadcast = text;
    bcastIdx = 0;
    if (bcastTimer) clearInterval(bcastTimer);
    bcastTimer = setInterval(() => {
        if (!broadcast.length) return;
        const c = broadcast.charCodeAt(bcastIdx);
        if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'oracle', val: c, target: -1 }));
        bcastIdx = (bcastIdx + 1) % broadcast.length;
    }, 500);
});

// ── Filter Toggle ────────────────────────────────────────
document.getElementById('filter-success').addEventListener('change', e => {
    const hide = e.target.checked;
    document.querySelectorAll('.log-fail').forEach(el => { el.style.display = hide ? 'none' : 'block'; });
    termOut.scrollTop = termOut.scrollHeight;
});

// ── Library Inject ───────────────────────────────────────
document.getElementById('btn-inject-lib').addEventListener('click', () => {
    const sel = document.getElementById('library-select');
    if (!sel.value) return;
    const [cat, book] = sel.value.split('|');
    if (ws && ws.readyState === 1) {
        ws.send(JSON.stringify({ type: 'inject_curriculum_file', category: cat, book_name: book }));
        tprint('› Injected: [' + cat + '] ' + book, 't-sys');
    }
});

document.getElementById('btn-inject-custom').addEventListener('click', () => {
    const inp = document.getElementById('custom-book-input');
    if (!inp.value) return;
    if (ws && ws.readyState === 1) {
        ws.send(JSON.stringify({ type: 'inject_custom_book', text: inp.value }));
        tprint('› Injected custom: "' + inp.value + '"', 't-sys');
        inp.value = '';
    }
});
