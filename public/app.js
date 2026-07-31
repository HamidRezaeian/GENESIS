/* ═══════════════════════════════════════════════════════════
   GENESIS — Neuromorphic Observation Deck (app.js)
   Observer Mode: Real-time Telemetry & Neocortical SNN Visualizer
   ═══════════════════════════════════════════════════════════ */

// ── Canvas Setup & Dynamic Zoom ──────────────────────────
const canvas = document.getElementById('ramCanvas');
const ctx = canvas.getContext('2d', { alpha: false });
canvas.width = 256;
canvas.height = 256;
let imgData = ctx.createImageData(256, 256);
let rawRamBytes = new Uint8Array(256 * 256);
let activeLegendFilter = null;

// Zoom & Fullscreen Controls
const btnFit = document.getElementById('btn-zoom-fit');
const btn2x = document.getElementById('btn-zoom-2x');
const btnFull = document.getElementById('btn-fullscreen');

if (btnFit && btn2x) {
    btnFit.addEventListener('click', () => {
        canvas.classList.remove('zoom-2x');
        btnFit.classList.add('active');
        btn2x.classList.remove('active');
    });
    btn2x.addEventListener('click', () => {
        canvas.classList.add('zoom-2x');
        btn2x.classList.add('active');
        btnFit.classList.remove('active');
    });
}

if (btnFull) {
    btnFull.addEventListener('click', () => {
        const container = document.getElementById('canvas-container') || document.body;
        if (!document.fullscreenElement) {
            if (container.requestFullscreen) container.requestFullscreen();
        } else {
            if (document.exitFullscreen) document.exitFullscreen();
        }
    });
}

// Interactive Legend Filtering
document.querySelectorAll('.legend-item').forEach(item => {
    item.addEventListener('mouseenter', () => {
        activeLegendFilter = item.getAttribute('data-type');
        renderRamCanvas();
    });
    item.addEventListener('mouseleave', () => {
        activeLegendFilter = null;
        renderRamCanvas();
    });
});

// RAM Tooltip on Canvas Hover
const tooltip = document.getElementById('ram-tooltip');
canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const dim = canvas.width || 1024;
    const scaleX = dim / rect.width;
    const scaleY = dim / rect.height;
    const x = Math.floor((e.clientX - rect.left) * scaleX);
    const y = Math.floor((e.clientY - rect.top) * scaleY);

    if (x >= 0 && x < dim && y >= 0 && y < dim) {
        const addr = y * dim + x;
        const val = rawRamBytes[addr] || 0;
        const hex = '0x' + val.toString(16).padStart(2, '0').toUpperCase();
        const char = (val >= 32 && val <= 126) ? `'${String.fromCharCode(val)}'` : 'Non-printable';
        
        if (tooltip) {
            tooltip.classList.remove('hidden');
            tooltip.innerHTML = `<strong>Addr 0x${addr.toString(16).padStart(5, '0').toUpperCase()}</strong> (${x}, ${y}) | Val: ${val} (${hex}) | Char: ${char}`;
        }
    }
});

canvas.addEventListener('mouseleave', () => {
    if (tooltip) tooltip.classList.add('hidden');
});

// ── WebSocket Connection ─────────────────────────────────
let ws = null;
function connect() {
    const rawHost = window.location.hostname || '127.0.0.1';
    const host = (rawHost === 'localhost') ? '127.0.0.1' : rawHost;
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
        try {
            const d = JSON.parse(e.data);
            console.log('[WS Telemetry Received]', d.type, 'tick:', d.tick, 'sim_ready:', d.sim_ready);
            if (d.type === 'state') onState(d);
            else if (d.type === 'status') onBrain(d);
        } catch (err) {
            console.error('[WS Parse Error]', err);
        }
    };
}
connect();

// ── State Handler & Renderer ─────────────────────────────
let lastTick = 0, lastTime = performance.now();
let lastExtinctions = -1;
let currentServerState = null;

function onState(s) {
    console.log('[onState Render]', 'tick:', s.tick, 'pop:', s.pop, 'status:', s.status);
    currentServerState = s;
    const setTxt = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    
    if (s.status === 'initializing') {
        setTxt('val-tick', 'INIT...');
        return;
    }

    setTxt('val-tick', s.tick !== undefined ? s.tick.toLocaleString() : '0');
    if (document.getElementById('val-pop')) {
        document.getElementById('val-pop').innerHTML = (s.pop || 0).toLocaleString() + '<span class="dim">/' + (s.max_pop || 600) + '</span>';
    }
    setTxt('val-ext', s.extinctions !== undefined ? s.extinctions.toLocaleString() : '0');
    setTxt('val-elite-age', s.elite_age !== undefined ? s.elite_age.toLocaleString() : '0');
    // elite_iq is age ÷ neural footprint (a rate, NOT a percentage) — Rule-7 efficiency
    // proxy, observation-only; never presented as "prediction accuracy" (audit 2026-07-31).
    setTxt('val-elite-iq', s.elite_iq !== undefined ? String(s.elite_iq) : '—');
    setTxt('val-footprint', s.elite_footprint !== undefined ? s.elite_footprint.toLocaleString() + ' ATP/B' : '—');
    setTxt('val-agi-progress', s.agi_progress !== undefined ? s.agi_progress + '%' : '0%');
    setTxt('val-avg-age', s.avg_age !== undefined ? s.avg_age.toLocaleString() : '0');
    setTxt('val-refuges', s.num_refuge !== undefined ? s.num_refuge.toLocaleString() : '0');

    // Live cognition metrics
    if (s.metrics) {
        const m = s.metrics;
        setTxt('m-solve', m.solve_pct != null ? m.solve_pct.toFixed(0) + '%' : '—');
        setTxt('m-reads', (m.cum_reads || m.reads || 0).toLocaleString());
        setTxt('m-miss', (m.cum_miss || m.miss || 0).toLocaleString());
        setTxt('m-pred', (m.cum_pred || m.pred || 0).toLocaleString());
        setTxt('m-peer', (m.cum_peer || m.peer || 0).toLocaleString());
        setTxt('m-hact', m.hact != null ? m.hact.toFixed(2) : '—');
        setTxt('m-sensors', m.sensors || 0);
        setTxt('m-actuators', m.actuators || 0);
        setTxt('m-scratch', m.scratch || 0);
        if (s.universe_n !== undefined) setTxt('m-brainn', s.universe_n.toLocaleString());
    }

    // Cognitive Vocabulary Knowledge Base Grid
    if (s.vocab && document.getElementById('vocab-grid')) {
        const grid = document.getElementById('vocab-grid');
        if (s.vocab.length > 0) {
            grid.innerHTML = s.vocab.map(item => `
                <div class="vocab-badge">
                    <span class="v-char">${item.word}</span>
                    <span class="v-count">${item.count.toLocaleString()} solves</span>
                </div>
            `).join('');
        }
    }

    // Mastered Sentences Stream Rendering
    if (s.sentences && document.getElementById('sentence-list')) {
        const sList = document.getElementById('sentence-list');
        if (s.sentences.length > 0) {
            sList.innerHTML = s.sentences.map(sent => `
                <span class="sent-chip">💬 "${sent}"</span>
            `).join('');
        }
    }

    // Time-Series Analytics History
    if (s.history) {
        updateAnalyticsCharts(s.history);
    }

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
            text = "💥 <span class='text-crimson'>انقراض کلونی رخ داد!</span> نسل جدید از فسیل‌های الیت متولد شد.<br><br>";
        } else if (s.metrics && s.metrics.solve_pct !== undefined) {
            const pct = s.metrics.solve_pct;
            if (pct > 75) {
                text = "🧠 <span class='text-emerald'>ارگانیسم‌ها به پایداری کامل درک متنی رسیده‌اند!</span> پیش‌بینی دقیق توالی با موفقیت بالا انجام می‌شود.<br><br>";
            } else if (pct < 25) {
                text = "⚠️ <span class='text-amber'>ارگانیسم‌ها در فاز اکتشاف غیرایستا (REMAP) هستند.</span> اتصالات سیناپسی STDP3C در حال بازسازی است.<br><br>";
            } else {
                text = "🔍 ارگانیسم‌ها در حال چراگری، هضم و یادگیری الگوهای کتاب متنی هستند.<br><br>";
            }
        }
        
        if (s.elite_iq !== undefined) {
            let eliteDesc = `👑 <b>تحلیل ارگانیسم الیت (سن: ${s.elite_age} تیک)</b>: `;
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

    // Save RAM Bytes & Trigger Render
    if (s.ram_b64) {
        const bin = atob(s.ram_b64);
        const len = bin.length;
        const dim = Math.round(Math.sqrt(len));

        if (canvas.width !== dim || canvas.height !== dim) {
            canvas.width = dim;
            canvas.height = dim;
            imgData = ctx.createImageData(dim, dim);
            rawRamBytes = new Uint8Array(len);
            const badgeEl = document.querySelector('.badge');
            if (badgeEl) {
                badgeEl.textContent = `${dim} × ${dim} Memory Array (${(len / 1024).toFixed(0)}KB Substrate)`;
            }
        }

        for (let i = 0; i < len; i++) {
            rawRamBytes[i] = bin.charCodeAt(i);
        }
        renderRamCanvas();
    }
}

function renderRamCanvas() {
    if (!currentServerState || !imgData) return;
    const s = currentServerState;
    const px = imgData.data;
    const len = rawRamBytes.length;

    const orgPositions = s.org_positions || s.orgs || [];
    const orgPosSet = new Set(orgPositions);
    const screamingSet = new Set(s.screaming_orgs || []);
    const elitePos = s.elite_pos !== undefined ? s.elite_pos : -1;

    for (let i = 0; i < len; i++) {
        const v = rawRamBytes[i];
        const p = i << 2;
        let r = 7, g = 8, b = 14; // Default Background
        let cellType = "bg";

        if (v >= 32 && v <= 126) { r = 139; g = 92; b = 246; cellType = "book"; } // Books / Text (Purple)
        else { r = 7; g = 8; b = 14; cellType = "bg"; } // Empty RAM Substrate (Dark)

        // Overlay Organisms
        if (orgPosSet.has(i)) {
            cellType = "ip";
            if (i === elitePos) {
                r = 6; g = 182; b = 212; // Elite (Cyan)
            } else if (screamingSet.has(i)) {
                r = 234; g = 179; b = 8; cellType = "voice"; // Voice (Yellow)
            } else {
                r = 245; g = 158; b = 11; // Normal Organism (Orange)
            }
        }

        // Legend Filter Hover Effect
        if (activeLegendFilter && cellType !== activeLegendFilter) {
            r = Math.floor(r * 0.15);
            g = Math.floor(g * 0.15);
            b = Math.floor(b * 0.15);
        } else if (activeLegendFilter && cellType === activeLegendFilter) {
            r = Math.min(255, r + 50);
            g = Math.min(255, g + 50);
            b = Math.min(255, b + 50);
        }

        px[p] = r; px[p+1] = g; px[p+2] = b; px[p+3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);
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

// ── Human-Readable Neocortical Mapping ───────────────────
function getNeuronBioMeta(idStr) {
    // Map In/Out/H codes into clear Persian & English biological functions
    if (idStr.startsWith('In')) {
        const idx = parseInt(idStr.replace('In ', ''));
        if (idx < 23) {
            return {
                name: `👁️ دیداری RAM (بایت ${idx})`,
                cortex: 'Sensory',
                color: '#10b981',
                desc: `ورودی حس‌گر نوری/دیداری از آدرس بایت ${idx} در حافظه RAM`
            };
        } else if (idx === 23) {
            return {
                name: '⚡ ذخیره انرژی ATP',
                cortex: 'Sensory',
                color: '#f59e0b',
                desc: 'حس‌گر متابولیسم درونی: سطح فعلی انرژی ارگانیسم برای بقا'
            };
        } else {
            return {
                name: `📡 حس‌گر محیطی (پایه ${idx})`,
                cortex: 'Sensory',
                color: '#10b981',
                desc: 'ردیاب الگوی متنی/خوراک در خانه همسایه'
            };
        }
    } else if (idStr.startsWith('Out')) {
        const idx = parseInt(idStr.replace('Out ', ''));
        const motorMap = [
            { name: '🐾 حرکت مستقیم (Step Fwd)', desc: 'فرمان حرکتی پیشروی به سمت جلو در فضای RAM' },
            { name: '↩️ چرخش به چپ (Turn Left)', desc: 'تغییر زاویه دیداری ارگانیسم به سمت چپ' },
            { name: '↪️ چرخش به راست (Turn Right)', desc: 'تغییر زاویه دیداری ارگانیسم به سمت راست' },
            { name: '🍕 هضم و بلعیدن (Consume)', desc: 'جذب انرژی بایت‌های خوراک/کتاب در موقعیت فعلی' },
            { name: '🧬 تکثیر خودکار (Reproduce)', desc: 'انتقال ژنوم و متولد کردن ارگانیسم فرزند' },
            { name: '🗣️ انتشار صوت (Voice Out)', desc: 'انتشار بایت صوتی به ارگانیسم‌های همسایه' }
        ];
        const m = motorMap[idx] || { name: `🎬 محرک حرکتی ${idx}`, desc: 'خروجی رفتاری قشر حرکتی' };
        return {
            name: m.name,
            cortex: 'Motor',
            color: '#06b6d4',
            desc: m.desc
        };
    } else {
        // Interneurons / Neocortex
        const isExcitatory = !idStr.includes('-');
        return {
            name: `🧠 نئوکورتکس پردازشی (${idStr})`,
            cortex: 'Neocortex',
            color: isExcitatory ? '#8b5cf6' : '#ef4444',
            type: isExcitatory ? 'Excitatory (+)' : 'Inhibitory (-)',
            desc: isExcitatory ? 'نورون تحریکی قشر مخ: افزایش احتمال شلیک نورون‌های هدف' : 'نورون بازدارنده قشر مخ: کنترل و مهار شلیک‌های اضافی برای صرفه‌جویی در انرژی'
        };
    }
}

// ── Neural Circuit Visualizer (SVG + D3.js) ──────────────
let pathFilter = 'all'; // 'all', 'exc', 'inh'
let currentBrainSynapses = [];

const btnFilterAll = document.getElementById('btn-filter-all');
const btnFilterExc = document.getElementById('btn-filter-exc');
const btnFilterInh = document.getElementById('btn-filter-inh');

if (btnFilterAll && btnFilterExc && btnFilterInh) {
    btnFilterAll.addEventListener('click', () => { setPathFilter('all'); });
    btnFilterExc.addEventListener('click', () => { setPathFilter('exc'); });
    btnFilterInh.addEventListener('click', () => { setPathFilter('inh'); });
}

function setPathFilter(filter) {
    pathFilter = filter;
    [btnFilterAll, btnFilterExc, btnFilterInh].forEach(b => b.classList.remove('active'));
    if (filter === 'all') btnFilterAll.classList.add('active');
    if (filter === 'exc') btnFilterExc.classList.add('active');
    if (filter === 'inh') btnFilterInh.classList.add('active');
    if (currentBrainSynapses.length) renderBrainSVG(currentBrainSynapses);
}

function onBrain(d) {
    if (!d.elite) return;
    const statsEl = document.getElementById('brain-stats');
    if (statsEl) {
        statsEl.innerHTML = `
            <div style="display: flex; gap: 16px; margin-bottom: 12px; font-family: var(--mono); font-size: 12px; flex-wrap: wrap;">
                <span>👑 <b>Elite ID:</b> #${d.elite.id}</span>
                <span>⏳ <b>Age:</b> ${d.elite.age.toLocaleString()} Ticks</span>
                <span>🔬 <b>Viscosity:</b> ${d.elite.viscosity.toFixed(2)}</span>
                <span>🧬 <b>DNA:</b> <code style="color: var(--emerald);">${d.elite.genome_hex.slice(0, 16)}...</code></span>
                <span>⚡ <b>Active Synapses:</b> ${d.elite.synapses ? d.elite.synapses.length : 0}</span>
            </div>
        `;
    }
    if (d.elite.synapses) {
        currentBrainSynapses = d.elite.synapses;
        renderBrainSVG(d.elite.synapses);
    }
}

function renderBrainSVG(synapses) {
    const svg = d3.select('#brain-svg');
    svg.selectAll('*').remove();

    const wrapper = document.querySelector('.svg-wrapper');
    const width = wrapper ? wrapper.clientWidth : 700;
    const height = wrapper ? wrapper.clientHeight : 480;

    // Filter Synapses based on toggle
    let filteredSynapses = synapses;
    if (pathFilter === 'exc') filteredSynapses = synapses.filter(s => s.weight > 0);
    if (pathFilter === 'inh') filteredSynapses = synapses.filter(s => s.weight < 0);

    const nodeMap = new Map();
    filteredSynapses.forEach(s => {
        if (!nodeMap.has(s.source)) nodeMap.set(s.source, { id: s.source });
        if (!nodeMap.has(s.target)) nodeMap.set(s.target, { id: s.target });
    });

    const nodes = Array.from(nodeMap.values());
    const inNodes = nodes.filter(n => n.id.startsWith('In'));
    const outNodes = nodes.filter(n => n.id.startsWith('Out'));
    const hNodes = nodes.filter(n => !n.id.startsWith('In') && !n.id.startsWith('Out'));

    // Cortical Column Coordinates
    inNodes.forEach((n, i) => {
        n.x = 90;
        n.y = ((i + 1) * (height - 40)) / (inNodes.length + 1) + 20;
    });
    outNodes.forEach((n, i) => {
        n.x = width - 90;
        n.y = ((i + 1) * (height - 40)) / (outNodes.length + 1) + 20;
    });
    hNodes.forEach((n, i) => {
        n.x = width / 2 + (i % 2 === 0 ? -50 : 50);
        n.y = ((i + 1) * (height - 40)) / (hNodes.length + 1) + 20;
    });

    const g = svg.append('g');

    // Draw Bezier Curved Axon Paths
    g.append('g').selectAll('path')
        .data(filteredSynapses)
        .enter()
        .append('path')
        .attr('d', d => {
            const src = nodeMap.get(d.source);
            const dst = nodeMap.get(d.target);
            if (!src || !dst) return '';
            const dx = dst.x - src.x;
            const dy = dst.y - src.y;
            const cx1 = src.x + dx * 0.4;
            const cy1 = src.y;
            const cx2 = dst.x - dx * 0.4;
            const cy2 = dst.y;
            return `M ${src.x} ${src.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${dst.x} ${dst.y}`;
        })
        .attr('fill', 'none')
        .attr('stroke', d => d.weight > 0 ? '#10b981' : '#ef4444')
        .attr('stroke-opacity', 0.65)
        .attr('stroke-width', d => Math.min(Math.abs(d.weight) * 0.9 + 1.2, 5))
        .attr('class', 'axon-pulse');

    // Draw Neuron Nodes
    const nodeGroup = g.append('g').selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .attr('transform', d => `translate(${d.x}, ${d.y})`)
        .style('cursor', 'pointer')
        .on('click', (event, d) => inspectNeuron(d.id, synapses))
        .on('mouseenter', (event, d) => inspectNeuron(d.id, synapses));

    // Outer Glow Halo Ring
    nodeGroup.append('circle')
        .attr('r', 16)
        .attr('fill', 'none')
        .attr('stroke', d => getNeuronBioMeta(d.id).color)
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.5);

    // Core Neuron Body
    nodeGroup.append('circle')
        .attr('r', 12)
        .attr('fill', d => getNeuronBioMeta(d.id).color)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5);

    // Label Text
    nodeGroup.append('text')
        .text(d => d.id)
        .attr('dy', 4)
        .attr('text-anchor', 'middle')
        .attr('fill', '#fff')
        .attr('font-size', '9px')
        .attr('font-family', 'var(--mono)')
        .attr('font-weight', '700');
}

// ── Neuron Inspector HUD ─────────────────────────────────
function inspectNeuron(nodeId, synapses) {
    const meta = getNeuronBioMeta(nodeId);
    const titleEl = document.getElementById('insp-title');
    const bodyEl = document.getElementById('insp-body');

    if (titleEl) titleEl.textContent = `تحلیل نورون: ${meta.name}`;

    const incoming = synapses.filter(s => s.target === nodeId);
    const outgoing = synapses.filter(s => s.source === nodeId);

    let incHtml = incoming.map(s => `
        <div class="synapse-item">
            <span>${s.source} ➔ ${nodeId}</span>
            <span class="stdp-badge ${s.weight > 0 ? 'stdp-exc' : 'stdp-inh'}">${s.weight > 0 ? '+' : ''}${s.weight.toFixed(2)}</span>
        </div>
    `).join('');

    let outHtml = outgoing.map(s => `
        <div class="synapse-item">
            <span>${nodeId} ➔ ${s.target}</span>
            <span class="stdp-badge ${s.weight > 0 ? 'stdp-exc' : 'stdp-inh'}">${s.weight > 0 ? '+' : ''}${s.weight.toFixed(2)}</span>
        </div>
    `).join('');

    if (bodyEl) {
        bodyEl.innerHTML = `
            <div class="insp-card">
                <div class="insp-title">
                    <span>${meta.name}</span>
                    <span class="insp-tag" style="background:${meta.color}22; color:${meta.color}; border:1px solid ${meta.color}55;">${meta.cortex}</span>
                </div>
                <p style="margin-top:4px; font-size:11px; color:var(--text-muted);">${meta.desc}</p>
            </div>

            <div class="insp-card">
                <span class="b-label" style="margin-bottom:4px;">ورودی‌های سیناپسی (${incoming.length}):</span>
                <div class="synapse-list">${incHtml || '<span class="dim">بدون سیناپس ورودی</span>'}</div>
            </div>

            <div class="insp-card">
                <span class="b-label" style="margin-bottom:4px;">خروجی‌های آکسونی (${outgoing.length}):</span>
                <div class="synapse-list">${outHtml || '<span class="dim">بدون سیناپس خروجی</span>'}</div>
            </div>
        `;
    }
}

// ── Oracle Broadcast Terminal ─────────────────────────────
const termIn = document.getElementById('term-in');
if (termIn) {
    termIn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && termIn.value.trim() && ws) {
            const text = termIn.value.trim();
            ws.send(JSON.stringify({ type: 'inject_custom_book', text: text }));
            addTermLine('› [ORACLE INJECTED]: ' + text, 't-sys');
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

// ── Brain Modal Live Streaming ───────────────────────────
const btnBrain = document.getElementById('btn-brain');
const modal = document.getElementById('brain-modal');
const btnClose = document.getElementById('btn-close-modal');
let brainStreamInterval = null;

if (btnBrain && modal) {
    btnBrain.addEventListener('click', () => {
        modal.classList.remove('hidden');
        if (ws) ws.send(JSON.stringify({ type: 'get_brain' }));
        if (!brainStreamInterval) {
            brainStreamInterval = setInterval(() => {
                if (ws && modal && !modal.classList.contains('hidden')) {
                    ws.send(JSON.stringify({ type: 'get_brain' }));
                }
            }, 1000);
        }
    });
}

if (btnClose && modal) {
    btnClose.addEventListener('click', () => {
        modal.classList.add('hidden');
        if (brainStreamInterval) {
            clearInterval(brainStreamInterval);
            brainStreamInterval = null;
        }
    });
}


let lastHistoryData = null;


let chartIQ = null, chartPop = null, chartSNN = null, chartSolves = null;

function initAnalyticsCharts() {
    if (typeof Chart === 'undefined') return;

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { size: 10 } } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { size: 10 } } }
        }
    };

    const ctxIQ = document.getElementById('chart-iq');
    if (ctxIQ && !chartIQ) {
        chartIQ = new Chart(ctxIQ, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Elite IQ (%)', data: [], borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', fill: true, tension: 0.3 }] },
            options: { ...chartOptions, scales: { ...chartOptions.scales, y: { min: 0, max: 100 } } }
        });
    }

    const ctxPop = document.getElementById('chart-pop');
    if (ctxPop && !chartPop) {
        chartPop = new Chart(ctxPop, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Population', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.3 }] },
            options: chartOptions
        });
    }

    const ctxSNN = document.getElementById('chart-snn');
    if (ctxSNN && !chartSNN) {
        chartSNN = new Chart(ctxSNN, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Universe N (Neurons)', data: [], borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.1)', fill: true, tension: 0.3 }] },
            options: chartOptions
        });
    }

    const ctxSolves = document.getElementById('chart-solves');
    if (ctxSolves && !chartSolves) {
        chartSolves = new Chart(ctxSolves, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Cumulative Solves', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, tension: 0.3 }] },
            options: chartOptions
        });
    }
}

function updateAnalyticsCharts(history) {
    if (!history || history.length === 0) return;
    lastHistoryData = history;
    initAnalyticsCharts();
    const labels = history.map(h => h.tick.toLocaleString());
    
    if (chartIQ) {
        chartIQ.data.labels = labels;
        chartIQ.data.datasets[0].data = history.map(h => h.solve_pct !== undefined ? h.solve_pct : Math.min(100, h.iq || 0));
        chartIQ.update('none');
    }
    if (chartPop) {
        chartPop.data.labels = labels;
        chartPop.data.datasets[0].data = history.map(h => h.pop);
        chartPop.update('none');
    }
    if (chartSNN) {
        chartSNN.data.labels = labels;
        chartSNN.data.datasets[0].data = history.map(h => h.universe_n);
        chartSNN.update('none');
    }
    if (chartSolves) {
        chartSolves.data.labels = labels;
        chartSolves.data.datasets[0].data = history.map(h => h.cum_reads || h.cum_pred || 0);
        chartSolves.update('none');
    }
}


// ───────────── Tab Switching (Tab 1: Live, Tab 2: Analytics, Tab 3: Leaderboard) ─────────────
const btnTabLive = document.getElementById('tab-btn-live');
const btnTabAnalytics = document.getElementById('tab-btn-analytics');
const btnTabLeaderboard = document.getElementById('tab-btn-leaderboard');
const tabLive = document.getElementById('content');
const tabAnalytics = document.getElementById('analytics-section');
const tabLeaderboard = document.getElementById('leaderboard-section');

if (btnTabLive && btnTabAnalytics && btnTabLeaderboard) {
    btnTabLive.addEventListener('click', () => {
        btnTabLive.classList.add('active');
        btnTabAnalytics.classList.remove('active');
        btnTabLeaderboard.classList.remove('active');
        tabLive.classList.remove('hidden');
        tabAnalytics.classList.add('hidden');
        tabLeaderboard.classList.add('hidden');
    });

    btnTabAnalytics.addEventListener('click', () => {
        btnTabAnalytics.classList.add('active');
        btnTabLive.classList.remove('active');
        btnTabLeaderboard.classList.remove('active');
        tabAnalytics.classList.remove('hidden');
        tabLive.classList.add('hidden');
        tabLeaderboard.classList.add('hidden');
        setTimeout(() => {
            initAnalyticsCharts();
            if (lastHistoryData) updateAnalyticsCharts(lastHistoryData);
            if (chartIQ) chartIQ.resize();
            if (chartPop) chartPop.resize();
            if (chartSNN) chartSNN.resize();
            if (chartSolves) chartSolves.resize();
        }, 60);
    });

    btnTabLeaderboard.addEventListener('click', () => {
        btnTabLeaderboard.classList.add('active');
        btnTabLive.classList.remove('active');
        btnTabAnalytics.classList.remove('active');
        tabLeaderboard.classList.remove('hidden');
        tabLive.classList.add('hidden');
        tabAnalytics.classList.add('hidden');
    });
}

// ───────────── View Switcher Bar inside Leaderboard (Views A–C) ─────────────
const viewBtnA = document.getElementById('view-btn-a');
const viewBtnB = document.getElementById('view-btn-b');
const viewBtnC = document.getElementById('view-btn-c');
const viewATable = document.getElementById('view-a-table');
const viewBTable = document.getElementById('view-b-table');
const viewCTable = document.getElementById('view-c-table');

function showLeaderboardView(view) {
    [viewATable, viewBTable, viewCTable].forEach(t => { if (t) t.classList.add('hidden'); });
    [viewBtnA, viewBtnB, viewBtnC].forEach(b => { if (b) b.classList.remove('active'); });
    if (view === 'a' && viewATable) { viewATable.classList.remove('hidden'); viewBtnA.classList.add('active'); }
    if (view === 'b' && viewBTable) {
        viewBTable.classList.remove('hidden');
        viewBtnB.classList.add('active');
        // NOTE (audit 2026-07-31): no live values are injected into this table — no certified
        // 5-task run exists; injecting colony solve% into fabricated task rows was a false
        // attribution (and the hardcoded solve% fallback was fabricated telemetry). Cells
        // stay "—"; live rows become meaningful only after a real certified run publishes.
    }
    if (view === 'c' && viewCTable) {
        viewCTable.classList.remove('hidden');
        viewBtnC.classList.add('active');
        // Same honesty rule: no 65536/universe_n injection into fabricated efficiency rows.
    }
}

if (viewBtnA) viewBtnA.addEventListener('click', () => showLeaderboardView('a'));
if (viewBtnB) viewBtnB.addEventListener('click', () => showLeaderboardView('b'));
if (viewBtnC) viewBtnC.addEventListener('click', () => showLeaderboardView('c'));
