/* ═══════════════════════════════════════════════════════════
   GENESIS — Neuromorphic Observation Deck & Leaderboard (app.js)
   Observer Mode: Real-time Telemetry, Neocortical SNN & Leaderboard Deck
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
    const scale = rect.width / dim;
    const x = Math.floor((e.clientX - rect.left) / scale);
    const y = Math.floor((e.clientY - rect.top) / scale);
    if (x >= 0 && x < dim && y >= 0 && y < dim) {
        const idx = y * dim + x;
        const val = rawRamBytes[idx] || 0;
        tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
        tooltip.style.top = (e.clientY - rect.top + 15) + 'px';
        tooltip.innerHTML = `<strong>RAM Address:</strong> 0x${idx.toString(16).toUpperCase().padStart(5, '0')}<br><strong>Offset:</strong> [${x}, ${y}]<br><strong>Byte Value:</strong> ${val} (0x${val.toString(16).padStart(2,'0')})`;
        tooltip.classList.remove('hidden');
    }
});
canvas.addEventListener('mouseleave', () => tooltip.classList.add('hidden'));

function renderRamCanvas() {
    const data = imgData.data;
    for (let i = 0; i < 256 * 256; i++) {
        const val = rawRamBytes[i];
        const ptr = i * 4;
        if (val === 0) {
            data[ptr] = 10; data[ptr+1] = 15; data[ptr+2] = 26; data[ptr+3] = 255;
        } else if (val > 200) {
            data[ptr] = 245; data[ptr+1] = 158; data[ptr+2] = 11; data[ptr+3] = 255;
        } else if (val > 100) {
            data[ptr] = 139; data[ptr+1] = 92; data[ptr+2] = 246; data[ptr+3] = 255;
        } else {
            data[ptr] = 16; data[ptr+1] = 185; data[ptr+2] = 129; data[ptr+3] = 255;
        }
    }
    ctx.putImageData(imgData, 0, 0);
}

// ── Tab Switching (Tab 1: Live, Tab 2: Analytics, Tab 3: Leaderboard) ─────
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

// View Switcher Bar inside Leaderboard
const viewBtnA = document.getElementById('view-btn-a');
const viewBtnB = document.getElementById('view-btn-b');
const viewBtnC = document.getElementById('view-btn-c');

if (viewBtnA && viewBtnB && viewBtnC) {
    viewBtnA.addEventListener('click', () => {
        viewBtnA.classList.add('active'); viewBtnB.classList.remove('active'); viewBtnC.classList.remove('active');
    });
    viewBtnB.addEventListener('click', () => {
        viewBtnB.classList.add('active'); viewBtnA.classList.remove('active'); viewBtnC.classList.remove('active');
    });
    viewBtnC.addEventListener('click', () => {
        viewBtnC.classList.add('active'); viewBtnA.classList.remove('active'); viewBtnB.classList.remove('active');
    });
}

// Initialize Canvas
renderRamCanvas();
