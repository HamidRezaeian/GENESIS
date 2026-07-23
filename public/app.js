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
// Chart removed to make room for Behavior Summary

// ── WebSocket ─────────────────────────────────────────────
let ws = null;
function connect() {
    const host = window.location.hostname || '127.0.0.1';
    ws = new WebSocket('ws://' + host + ':8085');
    ws.onopen = () => {
        const dot = document.getElementById('status-dot');
        if (dot) dot.style.background = '#34d399';
        const libSel = document.getElementById('library-select');
        if (libSel) ws.send(JSON.stringify({ type: 'get_library' }));
        const slider = document.getElementById('energy-rate-slider');
        if (slider) {
            const v = parseInt(slider.value);
            ws.send(JSON.stringify({ type: 'set_energy_rate', rate: v / 1000 }));
        }
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
let lastExtinctions = -1;
const hideFails = () => document.getElementById('filter-success').checked;

function onState(s) {
    // KPI updates (cheap DOM writes)
    document.getElementById('val-tick').textContent = s.tick.toLocaleString();
    document.getElementById('val-pop').innerHTML = s.pop.toLocaleString() + '<span class="dim">/' + s.max_pop + '</span>';
    document.getElementById('val-ext').textContent = s.extinctions.toLocaleString();
    if (s.elite_age !== undefined) document.getElementById('val-elite-age').textContent = s.elite_age.toLocaleString();
    if (s.elite_iq !== undefined) document.getElementById('val-elite-iq').textContent = s.elite_iq + '%';
    if (s.agi_progress !== undefined) document.getElementById('val-agi-progress').textContent = s.agi_progress + '%';
    if (s.avg_age !== undefined) document.getElementById('val-avg-age').textContent = s.avg_age.toLocaleString();
    if (s.num_refuge !== undefined) document.getElementById('val-refuges').textContent = s.num_refuge.toLocaleString();

    // Live cognition metrics (2026-07-18: dashboard kept honest with the engine)
    if (s.metrics) {
        const m = s.metrics;
        const setTxt = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        setTxt('m-solve', m.solve_pct != null ? m.solve_pct.toFixed(0) + '%' : '—');
        setTxt('m-reads', m.reads);
        setTxt('m-miss', m.miss);
        setTxt('m-pred', m.pred);
        setTxt('m-peer', m.peer);
        setTxt('m-hact', m.hact != null ? m.hact.toFixed(2) : '—');
        setTxt('m-sensors', m.sensors);
        setTxt('m-actuators', m.actuators);
        setTxt('m-scratch', m.scratch || 0);
        if (s.universe_n !== undefined) setTxt('m-brainn', s.universe_n.toLocaleString());
    }
    // Feature-flag reflection: show which engine modes are live, hide metrics with no active flag
    if (s.flags) applyFlags(s.flags);

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

    // Behavior Summary
    const behavEl = document.getElementById('behavior-text');
    if (behavEl) {
        let text = "";
        if (lastExtinctions !== -1 && s.extinctions > lastExtinctions) {
            text = "💥 انقراض رخ داد! نسل فعلی نابود شد و نسل جدید با جهش‌های ژنتیکی جدید متولد شد.\\n\\n";
        } else if (s.metrics && s.metrics.solve_pct !== undefined) {
            const pct = s.metrics.solve_pct;
            if (pct > 75) {
                text = "🧠 ارگانیسم‌ها باهوش شده‌اند! با درصد بالایی زنده می‌مانند و خطرها را پیش‌بینی می‌کنند.\\n\\n";
            } else if (pct < 25) {
                text = "⚠️ ارگانیسم‌ها سردرگم هستند. مرگ و میر بالاست و در تقلا برای درک محیط هستند.\\n\\n";
            } else {
                text = "🔍 ارگانیسم‌ها در حال کاوش، آزمون و خطا، و یادگیری تدریجی الگوهای محیط هستند.\\n\\n";
            }
        }
        
        // Elite Behavior Analysis
        if (s.elite_iq !== undefined) {
            let eliteDesc = `👑 **رفتار الیت (باهوش‌ترین موجود با سن ${s.elite_age} و هوش ${s.elite_iq}%)**: `;
            
            if (s.elite_iq > 80) {
                eliteDesc += "مغز الیت بسیار پیشرفته شده است. او محیط را به خوبی درک می‌کند ";
                if (s.metrics && s.metrics.pred > 5) {
                    eliteDesc += "و توانایی شگفت‌انگیزی در «پیش‌بینی» اتفاقات آینده پیدا کرده است. ";
                } else {
                    eliteDesc += "و به سرعت واکنش نشان می‌دهد. ";
                }
            } else if (s.elite_iq > 40) {
                eliteDesc += "مغز الیت در مرحله یادگیری الگوهاست و تا حدودی ارتباط سنسورها با موتورهای حرکتی را کشف کرده است. ";
            } else {
                eliteDesc += "مغز الیت هنوز نتوانسته ساختار پیچیده‌ای برای بقا شکل دهد و بیشتر بر اساس شانس زنده مانده است. ";
            }

            if (s.metrics && s.metrics.hact !== undefined) {
                if (s.metrics.hact < 0.5) {
                    eliteDesc += "همچنین حرکات او کاملاً هدفمند، بهینه‌سازی شده و دقیق است (آنتروپی پایین).";
                } else if (s.metrics.hact > 1.5) {
                    eliteDesc += "با این حال، هنوز حرکات تصادفی و اکتشافی (آزمون و خطا) در رفتار او دیده می‌شود.";
                }
            }
            text += eliteDesc;
        }
        behavEl.innerHTML = text.replace(/\\n/g, "<br>");
    }
    lastExtinctions = s.extinctions;

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
            else if (v === 0xAA) { r = 56; g = 189; b = 248; }
            else if (v >= 32 && v <= 126) { r = 167; g = 139; b = 250; }

            if (window._hl && window._hl !== (v === 0x55 ? 'energy' : v === 0xAA ? 'shelter' : v >= 32 && v <= 126 ? 'book' : null)) {
                r = r >> 3; g = g >> 3; b = b >> 3;
            }

            px[p] = r; px[p+1] = g; px[p+2] = b; px[p+3] = 255;
        }

        const orgs = s.orgs;
        const org_ages = s.org_ages || [];
        const org_iqs = s.org_iqs || [];
        const screaming = new Set(s.screaming_orgs || []);
        for (let i = 0; i < orgs.length; i++) {
            const pos = orgs[i];
            if (pos >= 0 && pos < len) {
                const p = pos << 2;
                const sc = screaming.has(pos);
                const isElite = (pos === s.elite_pos);
                const type = sc ? 'voice' : 'ip';
                let r, g, b;
                if (isElite) { r = 255; g = 255; b = 255; }
                else if (sc) { r = 250; g = 204; b = 21; }
                else { r = 96; g = 165; b = 250; }
                if (window._hl && window._hl !== type) { r >>= 3; g >>= 3; b >>= 3; }
                px[p] = r; px[p+1] = g; px[p+2] = b;
            }
        }
        ctx.putImageData(imgData, 0, 0);

        const w = canvas.width;
        const maxAge = s.elite_age || 1;

        for (let i = 0; i < orgs.length; i++) {
            const pos = orgs[i];
            if (pos < 0 || pos >= len) continue;
            const age = org_ages[i] || 0;
            const iq = org_iqs[i] || 0;
            const isElite = (pos === s.elite_pos);
            const x = pos % w;
            const y = Math.floor(pos / w);
            
            if (isElite) {
                // Elite glow scales with its IQ (baseline ~400 for a very smart elite)
                let iqRatio = Math.min((s.elite_iq || 0) / 400, 1.0);
                let eRad = 4 + (iqRatio * 4);
                let eBlur = 5 + (iqRatio * 15);
                let eOp = 0.4 + (iqRatio * 0.6);
                
                ctx.beginPath();
                ctx.arc(x, y, eRad, 0, 2 * Math.PI);
                ctx.fillStyle = `rgba(255, 255, 255, ${eOp})`;
                ctx.shadowColor = 'white';
                ctx.shadowBlur = eBlur;
                ctx.fill();
                
                ctx.beginPath();
                ctx.arc(x, y, 2, 0, 2 * Math.PI);
                ctx.fillStyle = '#facc15';
                ctx.fill();
                ctx.shadowBlur = 0;
            } else {
                // Normal organisms scale with IQ (baseline ~200 for bright)
                let ratio = Math.min(iq / 200, 1.0);
                if (ratio > 0.05) {
                    ctx.beginPath();
                    let rad = 2 + ratio * 3;
                    ctx.arc(x, y, rad, 0, 2 * Math.PI);
                    ctx.fillStyle = `rgba(96, 165, 250, ${0.2 + ratio * 0.6})`;
                    ctx.fill();
                }
            }
        }
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
            } else if (ev.type === 'peer_signal') {
                tprint('› Org #' + ev.org + ' Emergent Signal: ' + ev.msg, 't-out');
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
    if (!sel) return;
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
        'In 0': '⚡ Energy', 'In 1': '• Bias', 'In 2': '🌡 Crowd', 'In 3': '📡 OrcScalar',
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
if (slider) {
    slider.addEventListener('input', () => {
        const v = parseInt(slider.value);
        if (sliderVal) sliderVal.textContent = (v/10).toFixed(1) + '%';
        if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'set_energy_rate', rate: v/1000 }));
    });
}

// ── Oracle Terminal Input ────────────────────────────────
let broadcast = '', bcastIdx = 0, bcastTimer = null;
const termIn = document.getElementById('term-in');
if (termIn) {
    termIn.addEventListener('keydown', e => {
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
}

// ── Filter Toggle ────────────────────────────────────────
const filterSucc = document.getElementById('filter-success');
if (filterSucc) {
    filterSucc.addEventListener('change', e => {
        const hide = e.target.checked;
        document.querySelectorAll('.log-fail').forEach(el => { el.style.display = hide ? 'none' : 'block'; });
        termOut.scrollTop = termOut.scrollHeight;
    });
}

// ── Library Inject ───────────────────────────────────────
const btnInjectLib = document.getElementById('btn-inject-lib');
if (btnInjectLib) {
    btnInjectLib.addEventListener('click', () => {
        const sel = document.getElementById('library-select');
        if (!sel || !sel.value) return;
        const [cat, book] = sel.value.split('|');
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({ type: 'inject_curriculum_file', category: cat, book_name: book }));
            tprint('› Injected: [' + cat + '] ' + book, 't-sys');
        }
    });
}

const btnInjectCustom = document.getElementById('btn-inject-custom');
if (btnInjectCustom) {
    btnInjectCustom.addEventListener('click', () => {
        const inp = document.getElementById('custom-book-input');
        if (!inp || !inp.value) return;
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({ type: 'inject_custom_book', text: inp.value }));
            tprint('› Injected custom: "' + inp.value + '"', 't-sys');
            inp.value = '';
        }
    });
}

// ── Auto-inject toggle (survival scaffold, Ascent.md §5) ──
const autoInjectTog = document.getElementById('auto-inject-toggle');
if (autoInjectTog) {
    autoInjectTog.addEventListener('change', (e) => {
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({ type: 'set_auto_inject', enabled: e.target.checked }));
            tprint('› Auto-inject ' + (e.target.checked ? 'ON' : 'OFF'), 't-sys');
        }
    });
}

// ── Full-curriculum toggle + inject-all button ──
const currTog = document.getElementById('curriculum-toggle');
if (currTog) {
    currTog.addEventListener('change', (e) => {
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({ type: 'set_curriculum', enabled: e.target.checked }));
            tprint('› Full curriculum ' + (e.target.checked ? 'ON' : 'OFF'), 't-sys');
        }
    });
}
const btnInjectSeq = document.getElementById('btn-inject-seq');
if (btnInjectSeq) {
    btnInjectSeq.addEventListener('click', () => {
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({ type: 'inject_sequence' }));
            tprint('› Injected FULL curriculum (contiguous ladder)', 't-sys');
        }
    });
}

// ── Feature-flag reflection ──────────────────────────────
// Keep the dashboard honest with whatever engine mode is running: hide metrics whose flag is off,
// keep the auto-inject checkbox in sync with the server, render a compact live flag bar.
let _flagInit = false;
function applyFlags(f) {
    // sync the auto-inject checkbox to the server's authoritative state (once, and if it drifts)
    const ai = document.getElementById('auto-inject-toggle');
    if (ai && document.activeElement !== ai) ai.checked = !!f.auto_inject;
    // sync the full-curriculum checkbox
    const cu = document.getElementById('curriculum-toggle');
    if (cu && document.activeElement !== cu) cu.checked = !!f.curriculum;

    // sync readonly substrate toggles
    const di = document.getElementById('toggle-digestion');
    if (di && document.activeElement !== di) di.checked = !!f.digestion;
    const gr = document.getElementById('toggle-grounded');
    if (gr && document.activeElement !== gr) gr.checked = !!f.grounded;
    const ni = document.getElementById('toggle-niche');
    if (ni && document.activeElement !== ni) ni.checked = !!f.niche;

    // context-aware: dim Library panel if GROUNDED (books are irrelevant in pure food mode)
    const libPanel = document.getElementById('library-panel');
    if (libPanel) {
        if (f.grounded) {
            libPanel.style.opacity = '0.3';
            libPanel.style.pointerEvents = 'none';
        } else {
            libPanel.style.opacity = '1';
            libPanel.style.pointerEvents = 'auto';
        }
    }

    // show/hide flag-gated metrics
    document.querySelectorAll('.metric[data-flag]').forEach(el => {
        const on = !!f[el.getAttribute('data-flag')];
        el.style.display = on ? '' : 'none';
    });

    // library role label reflects the economy
    const role = document.getElementById('lib-role');
    if (role) role.textContent = f.economy === 'books' ? '(survival scaffold)' : '(' + f.economy + ')';

    // compact flag bar
    const bar = document.getElementById('flag-bar');
    if (bar) {
        const tags = [];
        if (f.peer) tags.push('PEER');
        if (f.redqueen) tags.push('RED-QUEEN');
        if (f.evosense) tags.push('EVO-SENSE');
        if (f.evoact) tags.push('EVO-ACT');
        if (f.niche) tags.push('NICHE-ECON');
        if (f.digestion) tags.push('DIGESTION');
        if (f.wmem) tags.push('WMEM-LATCH');
        if (f.grounded) tags.push('GROUNDED');
        if (f.remap) tags.push('REMAP');
        if (f.delay) tags.push('DELAY (N=' + (f.delay_n || 2) + ')');
        if (f.scratch) tags.push('SCRATCHPAD');
        bar.innerHTML = tags.length
            ? tags.map(t => '<span class="flag-tag">' + t + '</span>').join('')
            : '<span class="dim">baseline economy</span>';
    }
    _flagInit = true;
}

// ── Live Substrate Toggles ────────────────────────────────
const togDig = document.getElementById('toggle-digestion');
if (togDig) {
    togDig.addEventListener('change', (e) => {
        if (ws && ws.readyState === 1) {
            const grounded = document.getElementById('toggle-grounded').checked;
            const niche = document.getElementById('toggle-niche').checked;
            ws.send(JSON.stringify({ type: 'set_substrate', digestion: e.target.checked, grounded: grounded, niche: niche }));
            tprint('› Updating DIGESTION (Grounded Fuel) mode...', 't-sys');
        }
    });
}
const togGrounded = document.getElementById('toggle-grounded');
if (togGrounded) {
    togGrounded.addEventListener('change', (e) => {
        if (ws && ws.readyState === 1) {
            const digestion = document.getElementById('toggle-digestion') ? document.getElementById('toggle-digestion').checked : false;
            const niche = document.getElementById('toggle-niche') ? document.getElementById('toggle-niche').checked : false;
            ws.send(JSON.stringify({ type: 'set_substrate', grounded: e.target.checked, digestion: digestion, niche: niche }));
            tprint('› Restarting engine to apply GROUNDED substrate...', 't-sys');
        }
    });
}
const togNiche = document.getElementById('toggle-niche');
if (togNiche) {
    togNiche.addEventListener('change', (e) => {
        if (ws && ws.readyState === 1) {
            const digestion = document.getElementById('toggle-digestion') ? document.getElementById('toggle-digestion').checked : false;
            const grounded = document.getElementById('toggle-grounded') ? document.getElementById('toggle-grounded').checked : false;
            ws.send(JSON.stringify({ type: 'set_substrate', digestion: digestion, grounded: grounded, niche: e.target.checked }));
            tprint('› Restarting engine to apply NICHE economy...', 't-sys');
        }
    });
}


