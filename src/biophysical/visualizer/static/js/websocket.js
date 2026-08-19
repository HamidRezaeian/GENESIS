/**
 * websocket.js - real-time link to the running simulation.
 *
 * One `NeuronSocket` owns the connection to `/ws` and turns the server's JSON
 * frames into typed events.  There is no polling and no file loading here: the
 * solver thread pushes, this module dispatches.
 *
 * Server -> client message types
 *   hello   model description, sent once on connect
 *   status  transport state (state, t_ms, fps, speed, spike_count, config)
 *   state   one simulation frame (V_mV, g_Na_nS, g_K_nS, I_chan_pA, spikes)
 *   detail  full per-compartment readout (click-to-inspect)
 *   error   human-readable problem report
 *   pong    reply to our latency probe
 *
 * Client -> server commands are exposed as methods (start, pause, resume,
 * toggle, reset, stop, setSpeed, setStimulus, inspect).
 *
 * Usage:
 *   const sock = new NeuronSocket();
 *   sock.on('state', frame => renderer.update(frame));
 *   sock.connect();
 *   sock.start({ duration_ms: 30, amp_pA: 1500 });
 */

const DEFAULT_OPTIONS = {
  path: '/ws',
  reconnect: true,
  minBackoffMs: 400,
  maxBackoffMs: 8000,
  pingIntervalMs: 5000,
  maxQueued: 32,
};

export class NeuronSocket {
  /**
   * @param {string|null} url  Explicit ws:// URL, or null to derive from location.
   * @param {object}      opts Overrides for DEFAULT_OPTIONS.
   */
  constructor(url = null, opts = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...opts };
    this.url = url || NeuronSocket.defaultUrl(this.options.path);

    this.ws = null;
    this.state = 'idle';        // idle | connecting | open | closed
    this.attempts = 0;
    this.latencyMs = null;

    /** Last `hello` payload (model description). */
    this.info = null;
    /** Last `status` payload. */
    this.status = null;

    this._handlers = new Map();
    this._queue = [];
    this._reconnectTimer = null;
    this._pingTimer = null;
    this._closedByUser = false;
  }

  /** ws:// (or wss:// behind TLS) URL for the current page. */
  static defaultUrl(path = '/ws') {
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${scheme}//${window.location.host}${path}`;
  }

  // ------------------------------------------------------------------
  // Events
  // ------------------------------------------------------------------

  /**
   * Subscribe to a message type or a lifecycle event
   * ('open', 'close', 'reconnecting', 'any').
   * @returns {function} unsubscribe
   */
  on(type, handler) {
    if (!this._handlers.has(type)) this._handlers.set(type, new Set());
    this._handlers.get(type).add(handler);
    return () => this.off(type, handler);
  }

  off(type, handler) {
    const set = this._handlers.get(type);
    if (set) set.delete(handler);
  }

  _emit(type, payload) {
    const set = this._handlers.get(type);
    if (set) {
      for (const handler of set) {
        try {
          handler(payload);
        } catch (err) {
          console.error(`[NeuronSocket] handler for "${type}" threw:`, err);
        }
      }
    }
    if (type !== 'any') {
      const anySet = this._handlers.get('any');
      if (anySet) for (const handler of anySet) handler(payload, type);
    }
  }

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------

  get isOpen() {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  connect() {
    if (this.state === 'connecting' || this.isOpen) return this;
    this._closedByUser = false;
    this.state = 'connecting';
    this._emit('connecting', { url: this.url, attempt: this.attempts });

    let ws;
    try {
      ws = new WebSocket(this.url);
    } catch (err) {
      this._scheduleReconnect(err);
      return this;
    }
    this.ws = ws;

    ws.onopen = () => {
      this.state = 'open';
      this.attempts = 0;
      this._flush();
      this._startPing();
      this._emit('open', { url: this.url });
    };

    ws.onmessage = (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch (err) {
        console.warn('[NeuronSocket] non-JSON frame dropped', err);
        return;
      }
      this._dispatch(message);
    };

    ws.onerror = () => {
      // onclose always follows; reconnect logic lives there.
      this._emit('socketerror', { url: this.url });
    };

    ws.onclose = (event) => {
      this._stopPing();
      this.ws = null;
      const wasOpen = this.state === 'open';
      this.state = 'closed';
      this._emit('close', { code: event.code, reason: event.reason, wasOpen });
      if (!this._closedByUser && this.options.reconnect) this._scheduleReconnect();
    };

    return this;
  }

  /** Close and stop reconnecting. */
  disconnect() {
    this._closedByUser = true;
    this._stopPing();
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this.ws) this.ws.close(1000, 'client disconnect');
    this.ws = null;
    this.state = 'closed';
  }

  _scheduleReconnect(err) {
    if (this._reconnectTimer || this._closedByUser) return;
    this.attempts += 1;
    const { minBackoffMs, maxBackoffMs } = this.options;
    const delay = Math.min(maxBackoffMs, minBackoffMs * 2 ** (this.attempts - 1));
    const jittered = delay * (0.75 + Math.random() * 0.5);
    this._emit('reconnecting', { attempt: this.attempts, delayMs: Math.round(jittered), error: err });
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect();
    }, jittered);
  }

  // ------------------------------------------------------------------
  // Dispatch
  // ------------------------------------------------------------------

  _dispatch(message) {
    const type = message && message.type ? String(message.type) : 'unknown';

    if (type === 'hello') {
      this.info = message;
    } else if (type === 'status') {
      this.status = message;
    } else if (type === 'pong') {
      if (typeof message.t === 'number') {
        this.latencyMs = Math.max(0, performance.now() - message.t);
      }
      this._emit('latency', this.latencyMs);
      return;
    }

    this._emit(type, message);
  }

  // ------------------------------------------------------------------
  // Sending
  // ------------------------------------------------------------------

  /** Send a command; queued (bounded) while the socket is down. */
  send(message) {
    const payload = JSON.stringify(message);
    if (this.isOpen) {
      this.ws.send(payload);
      return true;
    }
    if (this._queue.length >= this.options.maxQueued) this._queue.shift();
    this._queue.push(payload);
    return false;
  }

  _flush() {
    while (this._queue.length && this.isOpen) {
      this.ws.send(this._queue.shift());
    }
  }

  _startPing() {
    this._stopPing();
    if (this.options.pingIntervalMs <= 0) return;
    this._pingTimer = setInterval(() => {
      if (this.isOpen) this.send({ type: 'ping', t: performance.now() });
    }, this.options.pingIntervalMs);
  }

  _stopPing() {
    if (this._pingTimer) {
      clearInterval(this._pingTimer);
      this._pingTimer = null;
    }
  }

  // ------------------------------------------------------------------
  // Control protocol
  // ------------------------------------------------------------------

  /** Start (or restart) the run. `config` fields are validated server-side. */
  start(config = null, restart = true) {
    return this.send({ type: 'start', config, restart });
  }

  pause() { return this.send({ type: 'pause' }); }

  resume() { return this.send({ type: 'resume' }); }

  toggle() { return this.send({ type: 'toggle' }); }

  reset(config = null) { return this.send({ type: 'reset', config }); }

  stop() { return this.send({ type: 'stop' }); }

  /** Playback speed multiplier, 0.1x .. 100x (paces frames, never dt). */
  setSpeed(value) { return this.send({ type: 'speed', value }); }

  /** Live stimulus edit: { amp_pA, onset_ms, dur_ms, target_idx, duration_ms }. */
  setStimulus(config) { return this.send({ type: 'stimulus', config }); }

  /**
   * Follow one compartment: the server then attaches a live `detail` block
   * (conductances + gate variables) to every subsequent state frame.
   * Pass null to stop following.
   */
  inspect(idx) { return this.send({ type: 'inspect', idx }); }
}

export default NeuronSocket;
