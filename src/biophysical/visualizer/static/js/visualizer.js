/**
 * visualizer.js - the application: scene, UI, and the live link to the solver.
 *
 * Responsibilities
 * ----------------
 * 1. Build a PBR scene (IBL + ACES tone mapping + bloom) and frame the cell.
 * 2. Fetch `/api/morphology` once and hand it to `NeuronMesh`.
 * 3. Open `/ws` and pump every `state` frame into the mesh, the trace and the
 *    status bar.  The render loop runs on requestAnimationFrame and is fully
 *    decoupled from the network, so a slow socket lowers the update rate of
 *    the data, never the frame rate of the view.
 * 4. Translate UI gestures into control messages.
 *
 * Nothing here computes physics.  Every number displayed came from
 * `ActiveSolver.step()` on the server.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

import { NeuronMesh } from './neuron.js';
import { NeuronSocket } from './websocket.js';

const $ = (id) => document.getElementById(id);
const TRACE_SAMPLES = 900;
const REGION_ORDER = [
  'SOMA', 'AIS', 'APICAL_TRUNK', 'APICAL_OBLIQUE',
  'APICAL_TUFT', 'BASAL', 'MYELIN', 'NODE', 'AXON_TERMINAL',
];

class Visualizer {
  constructor() {
    this.clock = new THREE.Clock();
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.pointerDown = new THREE.Vector2();

    this.morph = null;
    this.neuron = null;
    this.socket = null;
    this.info = null;
    this.status = null;

    this.trace = { t: [], soma: [], sel: [] };
    this.selected = -1;
    this.regionFilter = new Set();

    this.fps = 0;
    this._fpsSamples = [];
    this._lowFpsSince = 0;
    this._degraded = false;
    this._frameCount = 0;
  }

  /* ================================================================== */
  /* Boot                                                               */
  /* ================================================================== */

  async start() {
    this._setLoading('Starting WebGL');
    this._initScene();

    this._setLoading('Loading morphology from the live cell');
    try {
      this.morph = await this._fetchMorphology();
    } catch (err) {
      this._setLoading(`Could not load morphology: ${err.message}`);
      this._toast(`Morphology request failed: ${err.message}`);
      return;
    }

    this._setLoading('Building 224 compartments');
    this.neuron = new NeuronMesh(this.morph);
    this.scene.add(this.neuron.build());
    this._frameCamera();
    this._buildRegionChips();
    this._initTrace();
    this._bindUI();

    this._setLoading('Connecting to the solver');
    this._initSocket();

    this._hideLoading();
    this._animate();
  }

  async _fetchMorphology() {
    const response = await fetch('/api/morphology', { cache: 'no-store' });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const body = await response.json();
        if (body.error) detail = body.error;
      } catch (_) { /* not JSON */ }
      throw new Error(detail);
    }
    return response.json();
  }

  /* ================================================================== */
  /* Scene                                                              */
  /* ================================================================== */

  _initScene() {
    const container = $('viewport');

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.localClippingEnabled = true;
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x05070c);
    this.scene.fog = new THREE.FogExp2(0x05070c, 0.012);

    // Image-based lighting gives the translucent membrane something to refract.
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();

    this.camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.05, 400);
    this.camera.position.set(14, 6, 20);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.06;
    this.controls.rotateSpeed = 0.8;
    this.controls.panSpeed = 0.7;
    this.controls.minDistance = 0.4;
    this.controls.maxDistance = 160;

    const key = new THREE.DirectionalLight(0xdce9ff, 1.5);
    key.position.set(9, 14, 11);
    const fill = new THREE.DirectionalLight(0x5f86c8, 0.5);
    fill.position.set(-12, -4, -8);
    const rim = new THREE.DirectionalLight(0xffc98a, 0.65);
    rim.position.set(-6, 10, -14);
    this.scene.add(key, fill, rim, new THREE.HemisphereLight(0x9fc4ff, 0x0a0f18, 0.55));

    // Post-processing: bloom is what makes the AP read as a flash of light.
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight), 0.62, 0.55, 0.7,
    );
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());

    this.clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 100);

    window.addEventListener('resize', () => this._onResize());
    const canvas = this.renderer.domElement;
    canvas.addEventListener('pointerdown', (e) => {
      this.pointerDown.set(e.clientX, e.clientY);
    });
    canvas.addEventListener('pointerup', (e) => this._onPointerUp(e));
  }

  _frameCamera() {
    const bounds = this.morph.bounds;
    const scale = this.morph.render?.scale ?? 0.01;
    const centre = new THREE.Vector3(
      bounds.center[0] * scale, bounds.center[1] * scale, bounds.center[2] * scale,
    );
    const size = new THREE.Vector3(
      bounds.size[0] * scale, bounds.size[1] * scale, bounds.size[2] * scale,
    );
    const radius = Math.max(size.x, size.y, size.z) * 0.5;
    const distance = (radius / Math.tan((this.camera.fov * Math.PI) / 360)) * 1.35;

    this.controls.target.copy(centre);
    this.camera.position.set(
      centre.x + distance * 0.42,
      centre.y + distance * 0.16,
      centre.z + distance * 0.9,
    );
    this.camera.near = Math.max(0.02, distance / 900);
    this.camera.far = distance * 12;
    this.camera.updateProjectionMatrix();
    this.controls.update();

    this._modelRadius = radius;
    this.clipPlane.constant = radius * 4;
  }

  _onResize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.composer.setSize(w, h);
    this._resizeTrace();
  }

  /* ================================================================== */
  /* Socket                                                             */
  /* ================================================================== */

  _initSocket() {
    const socket = new NeuronSocket();
    this.socket = socket;

    socket.on('open', () => this._setConnection('live', 'live'));
    socket.on('close', () => this._setConnection('down', 'offline'));
    socket.on('reconnecting', (e) => this._setConnection('', `retry ${e.attempt}`));

    socket.on('hello', (message) => {
      this.info = message;
      this._applyInfo(message);
    });

    socket.on('status', (message) => {
      this.status = message;
      this._applyStatus(message);
    });

    socket.on('state', (frame) => this._onFrame(frame));

    socket.on('detail', (detail) => this._renderInspector(detail));

    socket.on('error', (message) => {
      this._toast(message.message || 'solver error');
    });

    socket.connect();
  }

  _onFrame(frame) {
    this.neuron.updateState(frame);

    // Trace: soma always, plus the selected compartment when one is followed.
    const t = frame.t_ms;
    const soma = frame.v_soma_mV ?? frame.V_mV[this.morph.soma_idx];
    this.trace.t.push(t);
    this.trace.soma.push(soma);
    this.trace.sel.push(this.selected >= 0 ? frame.V_mV[this.selected] : NaN);
    if (this.trace.t.length > TRACE_SAMPLES) {
      this.trace.t.shift();
      this.trace.soma.shift();
      this.trace.sel.shift();
    }

    this._setStat('val-time', `${t.toFixed(2)} ms`);
    this._setStat('val-vsoma', `${soma.toFixed(1)} mV`, soma > -20 ? 'hot' : 'cold');
    this._setStat('val-spikes', String(frame.spike_count ?? 0));
    if (frame.sim_state) this._setStat('val-state', frame.sim_state);

    if (frame.detail) this._renderInspector(frame.detail);
  }

  _applyInfo(info) {
    const parts = [
      `${info.n_compartments} compartments`,
      `${info.n_channels} channels`,
      info.solver,
      `dt ${info.dt_us} us`,
      `frame ${info.frame_dt_us} us`,
    ];
    $('model-line').textContent = parts.join(' | ');

    const config = info.config || {};
    if ($('in-amp')) $('in-amp').value = config.amp_pA ?? 1500;
    if ($('in-onset')) $('in-onset').value = config.onset_ms ?? 1;
    if ($('in-dur')) $('in-dur').value = config.dur_ms ?? 5;
    if ($('in-duration')) $('in-duration').value = config.duration_ms ?? 30;
    if ($('in-target')) $('in-target').value = config.target_idx ?? info.soma_idx ?? 0;

    // 1x playback = baseline_fps frames of stream_every timesteps each.
    const msPerSecond = (info.baseline_fps * info.frame_dt_us) / 1000;
    $('rate-note').textContent =
      `1x = ${msPerSecond.toFixed(1)} ms simulated per real second`;
  }

  _applyStatus(status) {
    const running = status.state === 'running';
    const button = $('btn-run');
    button.textContent = running ? 'Pause' : (status.state === 'paused' ? 'Resume' : 'Run');
    button.classList.toggle('running', running);

    this._setStat('val-state', status.state);
    this._setStat('val-speed', `${status.speed}x`);
    this._setStat('val-fps', `${this.fps.toFixed(0)} / ${status.fps}`);
    this._setStat('val-spikes', String(status.spike_count ?? 0));
    if (!running) this._setStat('val-time', `${status.t_ms.toFixed(2)} ms`);

    const slider = $('in-speed');
    if (slider && Math.abs(Number(slider.value) - Math.log10(status.speed)) > 0.01) {
      slider.value = Math.log10(status.speed);
      $('speed-value').textContent = `${status.speed}x`;
    }
  }

  /* ================================================================== */
  /* UI                                                                 */
  /* ================================================================== */

  _bindUI() {
    $('btn-run').addEventListener('click', () => {
      const state = this.status?.state;
      if (state === 'running') this.socket.pause();
      else if (state === 'paused') this.socket.resume();
      else this.socket.start(this._readConfig());
    });

    $('btn-reset').addEventListener('click', () => {
      this.trace = { t: [], soma: [], sel: [] };
      this.socket.reset(this._readConfig());
    });

    $('btn-fit').addEventListener('click', () => this._frameCamera());

    $('btn-apply').addEventListener('click', () => {
      this.socket.setStimulus(this._readConfig());
      this._toast('Stimulus updated - takes effect on the next timestep', false);
    });

    const speed = $('in-speed');
    speed.addEventListener('input', () => {
      const value = Math.round(10 ** Number(speed.value) * 100) / 100;
      $('speed-value').textContent = `${value}x`;
      this.socket.setSpeed(value);
    });

    $('in-mode').addEventListener('change', (e) => {
      const mode = Number(e.target.value);
      this.neuron.setMode(mode);
      const labels = ['Membrane potential', 'Live sodium conductance', 'Live potassium conductance', 'Peak channel density'];
      const ranges = [
        ['-90 mV', '+40 mV'],
        ['0', 'auto-scaled g_Na'],
        ['0', 'auto-scaled g_K'],
        ['0', 'max gbar'],
      ];
      $('legend-title').textContent = labels[mode];
      $('legend-min').textContent = ranges[mode][0];
      $('legend-max').textContent = ranges[mode][1];
      $('colorbar').classList.toggle('heat', mode !== 0);
    });

    const toggles = [
      ['chk-spines', (v) => this.neuron.setSpinesVisible(v)],
      ['chk-dots', (v) => this.neuron.setChannelDotsVisible(v)],
      ['chk-particles', (v) => this.neuron.setParticlesVisible(v)],
      ['chk-myelin', (v) => this.neuron.setMyelinVisible(v)],
      ['chk-bloom', (v) => { this.bloom.enabled = v; }],
    ];
    for (const [id, apply] of toggles) {
      const el = $(id);
      if (!el) continue;
      apply(el.checked);
      el.addEventListener('change', () => apply(el.checked));
    }

    const cutaway = $('chk-cutaway');
    const cutSlider = $('in-cut');
    const applyCut = () => {
      if (cutaway.checked) {
        this.clipPlane.constant = Number(cutSlider.value) * this._modelRadius;
        this.neuron.setClippingPlanes([this.clipPlane]);
      } else {
        this.neuron.setClippingPlanes(null);
      }
      cutSlider.disabled = !cutaway.checked;
    };
    cutaway.addEventListener('change', applyCut);
    cutSlider.addEventListener('input', applyCut);
    applyCut();

    $('insp-close').addEventListener('click', () => this._clearSelection());

    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      if (e.code === 'Space') { e.preventDefault(); this.socket.toggle(); }
      else if (e.key === 'r' || e.key === 'R') $('btn-reset').click();
      else if (e.key === 'f' || e.key === 'F') this._frameCamera();
      else if (e.key === 'Escape') this._clearSelection();
    });

    setTimeout(() => $('hint')?.classList.add('hidden'), 9000);
  }

  _readConfig() {
    const num = (id, fallback) => {
      const value = Number($(id)?.value);
      return Number.isFinite(value) ? value : fallback;
    };
    return {
      duration_ms: num('in-duration', 30),
      amp_pA: num('in-amp', 1500),
      onset_ms: num('in-onset', 1),
      dur_ms: num('in-dur', 5),
      target_idx: num('in-target', this.morph.soma_idx ?? 0),
    };
  }

  _buildRegionChips() {
    const host = $('regions');
    const present = new Set(this.morph.compartments.map((c) => c.type));
    const names = this.morph.region_names || {};
    const colors = this.morph.render?.region_colors || {};

    for (const type of REGION_ORDER) {
      if (!present.has(type)) continue;
      const button = document.createElement('button');
      button.className = 'chip';
      button.textContent = names[type] || type;
      button.style.borderColor = colors[type] || '';
      button.addEventListener('click', () => {
        if (this.regionFilter.has(type)) this.regionFilter.delete(type);
        else this.regionFilter.add(type);
        button.classList.toggle('on', this.regionFilter.has(type));
        this.neuron.setRegionFilter([...this.regionFilter]);
      });
      host.appendChild(button);
    }
  }

  /* ================================================================== */
  /* Picking + inspector                                                */
  /* ================================================================== */

  _onPointerUp(event) {
    // Ignore drags (orbiting) - only treat a near-stationary click as a pick.
    const moved = Math.hypot(event.clientX - this.pointerDown.x, event.clientY - this.pointerDown.y);
    if (moved > 4 || !this.neuron) return;

    this.pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
    this.pointer.y = -(event.clientY / window.innerHeight) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);

    const idx = this.neuron.pick(this.raycaster);
    if (idx < 0) {
      this._clearSelection();
      return;
    }
    this.selected = idx;
    this.neuron.setSelected(idx);
    this.socket.inspect(idx);          // server attaches live detail to frames
    $('inspector').classList.add('open');
  }

  _clearSelection() {
    this.selected = -1;
    this.neuron?.setSelected(null);
    this.socket?.inspect(null);
    $('inspector').classList.remove('open');
  }

  _renderInspector(detail) {
    if (!detail || detail.idx !== this.selected) return;

    $('insp-title').textContent = detail.name || `compartment ${detail.idx}`;
    $('insp-badge').textContent = detail.comp_type;

    const metrics = [
      ['V', `${detail.V_mV.toFixed(2)} mV`],
      ['g_Na', `${(detail.g_Na_nS ?? 0).toFixed(3)} nS`],
      ['g_K', `${(detail.g_K_nS ?? 0).toFixed(3)} nS`],
      ['I_chan', `${(detail.I_chan_pA ?? 0).toFixed(2)} pA`],
      ['diameter', `${detail.diameter_um.toFixed(2)} um`],
      ['length', `${detail.length_um.toFixed(2)} um`],
      ['area', `${detail.area_um2.toFixed(1)} um2`],
      ['C_m', `${detail.capacitance_pF.toFixed(3)} pF`],
      ['parent', detail.parent_idx < 0 ? 'none' : `#${detail.parent_idx}`],
      ['children', detail.children_idxs.length ? detail.children_idxs.map((c) => `#${c}`).join(' ') : 'none'],
    ];
    $('insp-metrics').innerHTML = metrics.map(([label, value]) => `
      <div class="metric">
        <span class="metric-label">${label}</span>
        <span class="metric-value">${value}</span>
      </div>`).join('');

    const channels = detail.channels || [];
    if (!channels.length) {
      $('insp-channels').innerHTML =
        '<div class="metric"><span class="metric-label">channels</span>'
        + '<span class="metric-value">none on this compartment</span></div>';
      return;
    }

    const rows = channels.map((channel) => {
      const gates = Object.entries(channel.gates || {}).map(([name, value]) => `
        ${name}=${value.toFixed(3)}
        <span class="gate-bar"><i style="width:${Math.round(Math.max(0, Math.min(1, value)) * 100)}%"></i></span>`).join(' ');
      return `<tr>
        <td>${channel.name}</td>
        <td>${channel.g_nS.toFixed(3)}</td>
        <td>${channel.g_max_nS.toFixed(3)}</td>
        <td>${(channel.open_fraction * 100).toFixed(2)}%</td>
        <td>${channel.E_rev_mV.toFixed(1)}</td>
        <td>${channel.I_pA.toFixed(2)}</td>
        <td style="text-align:left">${gates || '-'}</td>
      </tr>`;
    }).join('');

    $('insp-channels').innerHTML = `<table class="channels">
      <thead><tr>
        <th>channel</th><th>g (nS)</th><th>g_max (nS)</th><th>open</th>
        <th>E_rev (mV)</th><th>I (pA)</th><th style="text-align:left">gates</th>
      </tr></thead><tbody>${rows}</tbody></table>`;
  }

  /* ================================================================== */
  /* Voltage trace                                                      */
  /* ================================================================== */

  _initTrace() {
    this.traceCanvas = $('trace-canvas');
    this.traceCtx = this.traceCanvas.getContext('2d');
    this._resizeTrace();
  }

  _resizeTrace() {
    if (!this.traceCanvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = this.traceCanvas.getBoundingClientRect();
    this.traceCanvas.width = Math.max(1, Math.floor(rect.width * dpr));
    this.traceCanvas.height = Math.max(1, Math.floor(rect.height * dpr));
    this.traceCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this._traceSize = { w: rect.width, h: rect.height };
  }

  _drawTrace() {
    const ctx = this.traceCtx;
    if (!ctx || !this._traceSize) return;
    const { w, h } = this._traceSize;
    const vmin = -95;
    const vmax = 50;
    const toY = (mv) => h - ((mv - vmin) / (vmax - vmin)) * h;

    ctx.clearRect(0, 0, w, h);

    // grid + reference levels
    ctx.strokeStyle = 'rgba(120,160,210,0.13)';
    ctx.lineWidth = 1;
    ctx.font = '9px ui-monospace, monospace';
    ctx.fillStyle = 'rgba(140,165,200,0.55)';
    for (const mv of [-90, -70, -40, 0, 40]) {
      const y = toY(mv);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
      ctx.fillText(`${mv}`, 3, y - 2);
    }

    const n = this.trace.t.length;
    if (n < 2) return;
    const t0 = this.trace.t[0];
    const t1 = this.trace.t[n - 1];
    const span = Math.max(1e-6, t1 - t0);
    const toX = (t) => ((t - t0) / span) * w;

    const line = (values, colour, width) => {
      ctx.strokeStyle = colour;
      ctx.lineWidth = width;
      ctx.beginPath();
      let started = false;
      for (let i = 0; i < n; i += 1) {
        const v = values[i];
        if (!Number.isFinite(v)) { started = false; continue; }
        const x = toX(this.trace.t[i]);
        const y = toY(v);
        if (started) ctx.lineTo(x, y);
        else { ctx.moveTo(x, y); started = true; }
      }
      ctx.stroke();
    };

    if (this.selected >= 0) line(this.trace.sel, 'rgba(255,176,102,0.95)', 1.2);
    line(this.trace.soma, 'rgba(127,212,255,1)', 1.6);

    ctx.fillStyle = 'rgba(140,165,200,0.65)';
    ctx.fillText(`${t0.toFixed(1)} ms`, 3, h - 3);
    const label = `${t1.toFixed(1)} ms`;
    ctx.fillText(label, w - ctx.measureText(label).width - 3, h - 3);
  }

  /* ================================================================== */
  /* Render loop                                                        */
  /* ================================================================== */

  _animate() {
    const dt = Math.min(0.1, this.clock.getDelta());
    const elapsed = this.clock.elapsedTime;

    this.controls.update();
    this.neuron.update(dt, elapsed);
    this.neuron.updateLOD(this.camera, this._modelRadius * 3.2);
    this.composer.render();

    this._frameCount += 1;
    if (this._frameCount % 4 === 0) this._drawTrace();
    this._trackFps(dt);

    requestAnimationFrame(() => this._animate());
  }

  _trackFps(dt) {
    if (dt <= 0) return;
    this._fpsSamples.push(1 / dt);
    if (this._fpsSamples.length > 40) this._fpsSamples.shift();
    if (this._frameCount % 20) return;

    const sum = this._fpsSamples.reduce((a, b) => a + b, 0);
    this.fps = sum / this._fpsSamples.length;
    this._setStat('val-fps', `${this.fps.toFixed(0)} / ${this.status?.fps ?? 0}`,
      this.fps < 40 ? 'warn' : '');

    // Adaptive step-down: transmission and bloom are the two expensive passes.
    if (this._degraded || this.fps > 45) {
      this._lowFpsSince = 0;
      return;
    }
    if (!this._lowFpsSince) this._lowFpsSince = performance.now();
    else if (performance.now() - this._lowFpsSince > 3000) {
      this._degraded = true;
      for (const material of this.neuron._materials) {
        if (material.transmission !== undefined && material.transmission > 0) {
          material.transmission = 0;
          material.opacity = 0.94;
          material.transparent = true;
          material.needsUpdate = true;
        }
      }
      this.bloom.strength = 0.4;
      $('chk-spines').checked = false;
      this.neuron.setSpinesVisible(false);
      this._toast('Frame rate below 45 FPS - reduced translucency, bloom and spines', false);
    }
  }

  /* ================================================================== */
  /* Small helpers                                                      */
  /* ================================================================== */

  _setStat(id, value, className) {
    const el = $(id);
    if (!el) return;
    el.textContent = value;
    if (className !== undefined) el.className = `stat-value ${className || ''}`.trim();
  }

  _setConnection(state, label) {
    const el = $('conn');
    el.className = state;
    el.textContent = label;
  }

  _setLoading(text) {
    const el = $('loading-text');
    if (el) el.textContent = text;
  }

  _hideLoading() {
    $('loading')?.classList.add('hidden');
  }

  _toast(message, isError = true) {
    const el = $('toast');
    if (!el) return;
    el.textContent = message;
    el.style.background = isError ? 'rgba(70,18,18,0.92)' : 'rgba(18,42,60,0.92)';
    el.style.borderColor = isError ? 'rgba(255,107,107,0.45)' : 'rgba(127,212,255,0.4)';
    el.style.color = isError ? '#ffdede' : '#dceeff';
    el.classList.add('show');
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => el.classList.remove('show'), 4200);
  }
}

const app = new Visualizer();
app.start().catch((err) => {
  console.error(err);
  const el = document.getElementById('loading-text');
  if (el) el.textContent = `Startup failed: ${err.message}`;
});

window.genesis = app;   // handy in the console

export default app;
