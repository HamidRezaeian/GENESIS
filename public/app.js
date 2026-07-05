const MEM_SIZE = 131072;
const GRID_W = 512;
const GRID_H = 256;

const canvas = document.getElementById('ramCanvas');
const ctx = canvas.getContext('2d', { alpha: false });

// Set internal canvas resolution exactly to grid size for pixel-perfect rendering
canvas.width = GRID_W;
canvas.height = GRID_H;

// Create ImageData buffer for fast pixel manipulation
const imgData = ctx.createImageData(GRID_W, GRID_H);
const data = imgData.data;

// Parse the memory snapshot from base64 quickly
function base64ToUint8Array(base64) {
    const raw = window.atob(base64);
    const rawLength = raw.length;
    const array = new Uint8Array(new ArrayBuffer(rawLength));
    for(let i = 0; i < rawLength; i++) {
        array[i] = raw.charCodeAt(i);
    }
    return array;
}

// Colors
const COLOR_NOP = [0, 0, 0, 255];
const COLOR_CODE = [51, 119, 255, 255]; // Blueish for valid logic
const COLOR_IP = [0, 255, 157, 255]; // Neon Viridian

async function fetchState() {
    try {
        const res = await fetch('/api/state');
        if (!res.ok) return;
        const state = await res.json();
        
        if (!state.memory_b64) return;
        
        // Update DOM KPIs
        document.getElementById('val-cycles').innerText = state.tick.toLocaleString();
        document.getElementById('val-pop').innerHTML = `${state.pop.toLocaleString()} <span class="dim">/ ${state.max_pop}</span>`;
        document.getElementById('val-extinctions').innerText = state.extinctions;

        const memory = base64ToUint8Array(state.memory_b64);
        
        // Background Tectonic Ambient (based on zone 0 rate roughly)
        if(state.zones && state.zones.length > 0) {
            const z = state.zones[0];
            const ambient = document.getElementById('ambient-glow');
            if (z >= 3) {
                // Hot zone
                ambient.style.background = 'radial-gradient(circle, rgba(255,78,0,0.1) 0%, rgba(7,9,15,1) 60%)';
            } else {
                ambient.style.background = 'radial-gradient(circle, rgba(0,229,255,0.05) 0%, rgba(7,9,15,1) 60%)';
            }
        }

        // Draw Memory
        for (let i = 0; i < MEM_SIZE; i++) {
            const op = memory[i];
            const idx = i * 4;
            
            if (op === 0) {
                data[idx] = COLOR_NOP[0];
                data[idx+1] = COLOR_NOP[1];
                data[idx+2] = COLOR_NOP[2];
                data[idx+3] = 255;
            } else {
                // Add some variance based on opcode for texture
                const intensity = 100 + (op * 3);
                data[idx] = 20; // R
                data[idx+1] = intensity; // G
                data[idx+2] = Math.min(255, intensity + 100); // B
                data[idx+3] = 255;
            }
        }
        
        // Draw IPs as brilliant neon pixels over the data
        if (state.ips) {
            for (const ip of state.ips) {
                if (ip >= 0 && ip < MEM_SIZE) {
                    const idx = ip * 4;
                    data[idx] = COLOR_IP[0];
                    data[idx+1] = COLOR_IP[1];
                    data[idx+2] = COLOR_IP[2];
                    data[idx+3] = 255;
                }
            }
        }
        
        // Blit to canvas
        ctx.putImageData(imgData, 0, 0);
        
        // Optional: Draw zone overlays if needed, but keeping it clean for now.
        
    } catch (e) {
        console.error("Dashboard fetch error:", e);
    }
}

// Fetch 10 times a second
setInterval(fetchState, 100);
fetchState();
