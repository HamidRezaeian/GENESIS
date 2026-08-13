/**
 * neuron.js - builds the 3-D neuron and drives it from live solver state.
 *
 * Geometry
 * --------
 * `/api/morphology` gives one polyline per *section* (boundary points) plus a
 * radius at every boundary.  Each section becomes a centripetal
 * CatmullRomCurve3; each compartment is the slice of that curve between its
 * two boundaries, swept into a tube whose radius goes r0 -> r1.  That is what
 * makes dendrites taper continuously instead of looking like stacked pipes,
 * and because neighbouring compartments share a boundary point on a shared
 * curve the joints stay smooth.
 *
 * All compartment tubes (plus the soma ellipsoid) are merged into ONE
 * BufferGeometry with a per-vertex `aIndex` attribute, so the whole cell is a
 * single draw call.
 *
 * Live state
 * ----------
 * Per-frame values are uploaded as a 256x1 RGBA float texture:
 *
 *   R = normalised membrane voltage      (from V_mV)
 *   G = normalised live sodium conductance   (from g_Na_nS)
 *   B = normalised live potassium conductance (from g_K_nS)
 *   A = spike glow envelope (set on spike_events, decays)
 *
 * A second, rarely-updated "meta" texture carries:
 *
 *   R = region highlight weight, G = static g_Na density,
 *   B = static g_K density,      A = selection flag
 *
 * `MeshPhysicalMaterial.onBeforeCompile` injects a lookup into those textures,
 * so the material keeps real PBR shading (transmission, clearcoat, IBL) while
 * its colour and emissive come from the solver.  No per-frame CPU work beyond
 * writing two typed arrays.
 *
 * Radius scaling
 * --------------
 * True radii span 0.25 um (tuft tips) to 10 um (soma); drawn 1:1 the thin
 * branches vanish.  Radii are therefore compressed:
 *
 *   r_draw = min_radius_um + gain * r_um ** exponent      (exponent 0.7)
 *
 * Monotonic, so thicker is always thicker, and the soma stays close to life
 * size.  Set `radiusExponent: 1` and `radiusGain: 1` for true scale.
 */

import * as THREE from 'three';

const TEX_W = 256;               // >= 224 compartments, power of two
const SPIKE_TAU = 0.16;          // seconds, spike glow decay

/** Deterministic PRNG so spines never jitter between reloads. */
function mulberry32(seed) {
  let a = seed >>> 0;
  return function random() {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);

/* ------------------------------------------------------------------ */
/* GLSL fragments                                                      */
/* ------------------------------------------------------------------ */

const COMMON_GLSL = /* glsl */`
uniform sampler2D uState;
uniform sampler2D uMeta;
uniform float uMode;      // 0 voltage, 1 g_Na, 2 g_K, 3 channel density
uniform float uGlow;
uniform float uDim;       // brightness of non-highlighted regions
varying float vCompIdx;

vec3 rampVoltage(float x) {
  // hyperpolarised -> resting -> depolarised: blue -> purple -> orange -> red
  vec3 c0 = vec3(0.043, 0.129, 0.451);
  vec3 c1 = vec3(0.145, 0.361, 0.784);
  vec3 c2 = vec3(0.451, 0.318, 0.812);
  vec3 c3 = vec3(0.878, 0.416, 0.216);
  vec3 c4 = vec3(1.000, 0.196, 0.157);
  vec3 c = mix(c0, c1, smoothstep(0.00, 0.28, x));
  c = mix(c, c2, smoothstep(0.24, 0.52, x));
  c = mix(c, c3, smoothstep(0.50, 0.78, x));
  c = mix(c, c4, smoothstep(0.76, 1.00, x));
  return c;
}

vec3 rampHeat(float x) {
  vec3 c0 = vec3(0.035, 0.055, 0.098);
  vec3 c1 = vec3(0.106, 0.376, 0.510);
  vec3 c2 = vec3(0.271, 0.796, 0.686);
  vec3 c3 = vec3(0.984, 0.945, 0.639);
  vec3 c = mix(c0, c1, smoothstep(0.0, 0.35, x));
  c = mix(c, c2, smoothstep(0.3, 0.7, x));
  c = mix(c, c3, smoothstep(0.65, 1.0, x));
  return c;
}

vec4 compState() { return texture2D(uState, vec2((vCompIdx + 0.5) / ${TEX_W}.0, 0.5)); }
vec4 compMeta()  { return texture2D(uMeta,  vec2((vCompIdx + 0.5) / ${TEX_W}.0, 0.5)); }

float compValue(vec4 st, vec4 mt) {
  if (uMode < 0.5) return st.r;
  if (uMode < 1.5) return st.g;
  if (uMode < 2.5) return st.b;
  return mt.g;
}

vec3 compColor(vec4 st, vec4 mt) {
  float v = compValue(st, mt);
  return uMode < 0.5 ? rampVoltage(v) : rampHeat(v);
}
`;

/* ------------------------------------------------------------------ */
/* Tube construction                                                   */
/* ------------------------------------------------------------------ */

/**
 * Sweep a tapered tube along a slice of `curve`.
 * @returns {{position:Float32Array, normal:Float32Array, uv:Float32Array, index:Uint32Array}}
 */
function buildTube(curve, u0, u1, r0, r1, tubular, radial) {
  const pts = [];
  for (let i = 0; i <= tubular; i += 1) {
    pts.push(curve.getPointAt(u0 + (u1 - u0) * (i / tubular)));
  }
  const sub = new THREE.CatmullRomCurve3(pts, false, 'centripetal', 0.5);
  const frames = sub.computeFrenetFrames(tubular, false);

  const vertexCount = (tubular + 1) * (radial + 1);
  const position = new Float32Array(vertexCount * 3);
  const normal = new Float32Array(vertexCount * 3);
  const uv = new Float32Array(vertexCount * 2);
  const index = new Uint32Array(tubular * radial * 6);

  let p = 0;
  let n = 0;
  let t = 0;
  for (let i = 0; i <= tubular; i += 1) {
    const centre = pts[i];
    const N = frames.normals[i];
    const B = frames.binormals[i];
    const f = i / tubular;
    const radius = r0 + (r1 - r0) * f;
    for (let j = 0; j <= radial; j += 1) {
      const theta = (j / radial) * Math.PI * 2;
      const sin = Math.sin(theta);
      const cos = -Math.cos(theta);
      const nx = cos * N.x + sin * B.x;
      const ny = cos * N.y + sin * B.y;
      const nz = cos * N.z + sin * B.z;
      normal[n] = nx; normal[n + 1] = ny; normal[n + 2] = nz; n += 3;
      position[p] = centre.x + radius * nx;
      position[p + 1] = centre.y + radius * ny;
      position[p + 2] = centre.z + radius * nz;
      p += 3;
      uv[t] = f; uv[t + 1] = j / radial; t += 2;
    }
  }

  let k = 0;
  for (let i = 0; i < tubular; i += 1) {
    for (let j = 0; j < radial; j += 1) {
      const a = (radial + 1) * i + j;
      const b = (radial + 1) * (i + 1) + j;
      const c = (radial + 1) * (i + 1) + j + 1;
      const d = (radial + 1) * i + j + 1;
      index[k] = a; index[k + 1] = b; index[k + 2] = d;
      index[k + 3] = b; index[k + 4] = c; index[k + 5] = d;
      k += 6;
    }
  }
  return { position, normal, uv, index };
}

/** Merge chunks into one indexed BufferGeometry carrying `aIndex`. */
function mergeChunks(chunks) {
  let vertexCount = 0;
  let indexCount = 0;
  for (const chunk of chunks) {
    vertexCount += chunk.geom.position.length / 3;
    indexCount += chunk.geom.index.length;
  }

  const position = new Float32Array(vertexCount * 3);
  const normal = new Float32Array(vertexCount * 3);
  const uv = new Float32Array(vertexCount * 2);
  const aIndex = new Float32Array(vertexCount);
  const index = new Uint32Array(indexCount);

  let vOff = 0;
  let iOff = 0;
  for (const chunk of chunks) {
    const g = chunk.geom;
    const count = g.position.length / 3;
    position.set(g.position, vOff * 3);
    normal.set(g.normal, vOff * 3);
    uv.set(g.uv, vOff * 2);
    aIndex.fill(chunk.idx, vOff, vOff + count);
    for (let i = 0; i < g.index.length; i += 1) index[iOff + i] = g.index[i] + vOff;
    vOff += count;
    iOff += g.index.length;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(position, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(normal, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  geometry.setAttribute('aIndex', new THREE.BufferAttribute(aIndex, 1));
  geometry.setIndex(new THREE.BufferAttribute(index, 1));
  geometry.computeBoundingSphere();
  geometry.computeBoundingBox();
  return geometry;
}

/** Ellipsoid for the soma, emitted in the same chunk format. */
function somaChunk(centre, radius, widthSeg, heightSeg) {
  const sphere = new THREE.SphereGeometry(radius, widthSeg, heightSeg);
  sphere.scale(1.0, 1.22, 0.94);          // gentle pyramidal-soma ovoid
  sphere.translate(centre.x, centre.y, centre.z);
  const pos = sphere.getAttribute('position');
  const nor = sphere.getAttribute('normal');
  const uvs = sphere.getAttribute('uv');
  const idx = sphere.getIndex();
  const chunk = {
    position: new Float32Array(pos.array),
    normal: new Float32Array(nor.array),
    uv: new Float32Array(uvs.array),
    index: Uint32Array.from(idx.array),
  };
  sphere.dispose();
  return chunk;
}

/* ------------------------------------------------------------------ */
/* NeuronMesh                                                          */
/* ------------------------------------------------------------------ */

export class NeuronMesh {
  /**
   * @param {object} morph  payload from GET /api/morphology
   * @param {object} [opts]
   */
  constructor(morph, opts = {}) {
    const render = morph.render || {};
    this.morph = morph;
    this.opts = {
      scale: render.scale ?? 0.01,
      radiusGain: render.radius_gain ?? 2.4,
      radiusExponent: 0.7,
      minRadiusUm: render.min_radius_um ?? 0.32,
      voltageRange: render.voltage_range_mV ?? [-90, 40],
      spines: true,
      channelDots: true,
      particles: true,
      transmission: 0.35,
      ...opts,
    };

    this.group = new THREE.Group();
    this.group.name = 'neuron';

    this.compartments = morph.compartments || [];
    this.count = this.compartments.length;
    this.byIndex = new Map(this.compartments.map((c) => [c.idx, c]));

    // live + static texture backing stores
    this._stateData = new Float32Array(TEX_W * 4);
    this._metaData = new Float32Array(TEX_W * 4);
    this._gNaMax = 1e-9;
    this._gKMax = 1e-9;
    this.lastFrame = null;

    this._selected = -1;
    this._mode = 0;
    this._curves = new Map();
    this._materials = [];
    this._disposables = [];
    this._buildTextures();
  }

  /* -- radius mapping ------------------------------------------------ */

  _radius(rUm) {
    const { minRadiusUm, radiusGain, radiusExponent, scale } = this.opts;
    return (minRadiusUm + radiusGain * Math.pow(Math.max(rUm, 0.01), radiusExponent)) * scale;
  }

  _v3(point) {
    const s = this.opts.scale;
    return new THREE.Vector3(point[0] * s, point[1] * s, point[2] * s);
  }

  /* -- textures ------------------------------------------------------ */

  _buildTextures() {
    // Neutral start: everything at resting potential, no glow.
    const [vmin, vmax] = this.opts.voltageRange;
    const rest = clamp01((-70 - vmin) / (vmax - vmin));
    for (let i = 0; i < TEX_W; i += 1) this._stateData[i * 4] = rest;

    const maxNa = Math.max(this.morph.channel_max?.g_na ?? 1, 1e-9);
    const maxK = Math.max(this.morph.channel_max?.g_k ?? 1, 1e-9);
    for (const comp of this.compartments) {
      const o = comp.idx * 4;
      this._metaData[o] = 1;                                   // highlight
      this._metaData[o + 1] = clamp01((comp.g_na || 0) / maxNa); // static density
      this._metaData[o + 2] = clamp01((comp.g_k || 0) / maxK);
      this._metaData[o + 3] = 0;                                // selected
    }

    this.stateTexture = new THREE.DataTexture(this._stateData, TEX_W, 1, THREE.RGBAFormat, THREE.FloatType);
    this.stateTexture.minFilter = THREE.NearestFilter;
    this.stateTexture.magFilter = THREE.NearestFilter;
    this.stateTexture.needsUpdate = true;

    this.metaTexture = new THREE.DataTexture(this._metaData, TEX_W, 1, THREE.RGBAFormat, THREE.FloatType);
    this.metaTexture.minFilter = THREE.NearestFilter;
    this.metaTexture.magFilter = THREE.NearestFilter;
    this.metaTexture.needsUpdate = true;

    this.uniforms = {
      uState: { value: this.stateTexture },
      uMeta: { value: this.metaTexture },
      uMode: { value: 0 },
      uGlow: { value: 1 },
      uDim: { value: 1 },
      uTime: { value: 0 },
    };
  }

  /* -- materials ----------------------------------------------------- */

  _membraneMaterial() {
    const material = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      roughness: 0.34,
      metalness: 0.0,
      clearcoat: 0.55,
      clearcoatRoughness: 0.35,
      transmission: this.opts.transmission,
      thickness: 0.5,
      ior: 1.36,
      attenuationDistance: 3.0,
      attenuationColor: new THREE.Color(0x88bbff),
      sheen: 0.35,
      sheenColor: new THREE.Color(0x99ccff),
      emissive: new THREE.Color(0xffffff),
      emissiveIntensity: 1.0,
      side: THREE.FrontSide,
    });

    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.uniforms);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', `#include <common>\nattribute float aIndex;\nvarying float vCompIdx;`)
        .replace('#include <begin_vertex>', `#include <begin_vertex>\nvCompIdx = aIndex;`);
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>\n${COMMON_GLSL}`)
        .replace('#include <color_fragment>', `#include <color_fragment>
        vec4 gState = compState();
        vec4 gMeta = compMeta();
        vec3 gTint = compColor(gState, gMeta);
        float gHighlight = mix(uDim, 1.0, gMeta.r);
        diffuseColor.rgb *= gTint * gHighlight;`)
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        float gValue = compValue(gState, gMeta);
        float gRim = pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), 2.5);
        float gActive = smoothstep(0.58, 1.0, gValue);
        totalEmissiveRadiance = gTint * (gActive * 0.85 + gState.a * uGlow * 2.4) * gHighlight;
        totalEmissiveRadiance += gTint * gRim * 0.35 * gHighlight;
        totalEmissiveRadiance += vec3(0.35, 0.85, 1.0) * gMeta.a * (0.55 + 0.45 * sin(uTime * 6.0)) * gRim;`);
      material.userData.shader = shader;
    };
    material.customProgramCacheKey = () => 'genesis-membrane';
    this._materials.push(material);
    return material;
  }

  _myelinMaterial() {
    const material = new THREE.MeshPhysicalMaterial({
      color: 0xeef2f8,
      roughness: 0.62,
      metalness: 0.0,
      clearcoat: 0.3,
      sheen: 0.6,
      sheenColor: new THREE.Color(0xffffff),
      transparent: true,
      opacity: 0.55,
      transmission: 0.25,
      thickness: 0.4,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    this._materials.push(material);
    return material;
  }

  /* ================================================================== */
  /* Build                                                              */
  /* ================================================================== */

  build() {
    const sections = this.morph.sections || [];
    const somaIdx = this.morph.soma_idx ?? 0;

    const highChunks = [];
    const lowChunks = [];
    const myelinChunks = [];

    for (const section of sections) {
      const points = section.points.map((p) => this._v3(p));
      const n = section.comps.length;
      const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal', 0.5);
      this._curves.set(section.label, curve);

      const isMyelin = section.type === 'MYELIN';

      for (let k = 0; k < n; k += 1) {
        const idx = section.comps[k];
        if (idx === somaIdx) continue;               // soma drawn as an ellipsoid

        const comp = this.byIndex.get(idx);
        const r0 = this._radius(section.radii[k]);
        const r1 = this._radius(section.radii[k + 1]);
        const u0 = k / n;
        const u1 = (k + 1) / n;

        const thick = Math.max(r0, r1) / this.opts.scale;
        const radialHigh = thick > 3 ? 16 : thick > 1.2 ? 12 : 8;
        const tubHigh = Math.max(2, Math.min(6, Math.ceil((comp?.len_um ?? 10) / 9)));

        highChunks.push({ idx, geom: buildTube(curve, u0, u1, r0, r1, tubHigh, radialHigh) });
        lowChunks.push({ idx, geom: buildTube(curve, u0, u1, r0, r1, 1, 5) });

        if (isMyelin) {
          // Slightly inset + fattened sleeve: reads as a segmented sheath with
          // bare nodes of Ranvier showing between the internodes.
          const pad = 0.06 * (u1 - u0);
          myelinChunks.push({
            idx,
            geom: buildTube(curve, u0 + pad, u1 - pad, r0 * 2.05, r1 * 2.05, 2, 12),
          });
        }
      }
    }

    // -- soma ---------------------------------------------------------
    const soma = this.byIndex.get(somaIdx);
    if (soma) {
      const centre = this._v3(soma.c);
      const rSoma = this._radius((this.morph.render?.soma_radius_um) ?? soma.diam_um / 2);
      highChunks.push({ idx: somaIdx, geom: somaChunk(centre, rSoma, 40, 28) });
      lowChunks.push({ idx: somaIdx, geom: somaChunk(centre, rSoma, 14, 10) });
    }

    const membrane = this._membraneMaterial();

    this.geometryHigh = mergeChunks(highChunks);
    this.geometryLow = mergeChunks(lowChunks);
    this._disposables.push(this.geometryHigh, this.geometryLow);

    this.meshHigh = new THREE.Mesh(this.geometryHigh, membrane);
    this.meshHigh.name = 'membrane-high';
    this.meshLow = new THREE.Mesh(this.geometryLow, membrane);
    this.meshLow.name = 'membrane-low';
    this.meshLow.visible = false;
    this.group.add(this.meshHigh, this.meshLow);

    if (myelinChunks.length) {
      this.geometryMyelin = mergeChunks(myelinChunks);
      this._disposables.push(this.geometryMyelin);
      this.myelinMesh = new THREE.Mesh(this.geometryMyelin, this._myelinMaterial());
      this.myelinMesh.name = 'myelin';
      this.myelinMesh.renderOrder = 2;
      this.group.add(this.myelinMesh);
    }

    if (this.opts.spines) this._buildSpines();
    if (this.opts.channelDots) this._buildChannelDots();
    if (this.opts.particles) this._buildParticles();

    this.triangleCount = this.geometryHigh.index.count / 3
      + (this.geometryMyelin ? this.geometryMyelin.index.count / 3 : 0);

    return this.group;
  }

  /* -- dendritic spines --------------------------------------------- */

  _buildSpines() {
    const placements = [];
    for (const section of this.morph.sections || []) {
      const curve = this._curves.get(section.label);
      if (!curve) continue;
      const n = section.comps.length;
      for (let k = 0; k < n; k += 1) {
        const idx = section.comps[k];
        const comp = this.byIndex.get(idx);
        const want = comp?.spines || 0;
        if (!want) continue;
        const random = mulberry32(idx * 9781 + 17);
        const rBase = this._radius(section.radii[k]);
        for (let s = 0; s < want; s += 1) {
          const u = (k + (s + 0.5 + (random() - 0.5) * 0.7) / want) / n;
          const point = curve.getPointAt(Math.min(0.999, Math.max(0.001, u)));
          const tangent = curve.getTangentAt(Math.min(0.999, Math.max(0.001, u))).normalize();
          let axis = new THREE.Vector3(0, 1, 0);
          if (Math.abs(tangent.dot(axis)) > 0.9) axis = new THREE.Vector3(1, 0, 0);
          const perp = new THREE.Vector3().crossVectors(tangent, axis).normalize();
          const theta = random() * Math.PI * 2;
          const dir = perp.clone().applyAxisAngle(tangent, theta);
          const neck = rBase * (0.9 + random() * 0.8);
          placements.push({
            idx,
            position: point.clone().addScaledVector(dir, rBase + neck),
            scale: rBase * (0.55 + random() * 0.35),
          });
        }
      }
    }
    if (!placements.length) return;

    const geometry = new THREE.SphereGeometry(1, 7, 5);
    const material = this._membraneMaterial();
    material.transmission = 0;
    material.roughness = 0.45;

    const mesh = new THREE.InstancedMesh(geometry, material, placements.length);
    const indices = new Float32Array(placements.length);
    const matrix = new THREE.Matrix4();
    placements.forEach((p, i) => {
      matrix.makeScale(p.scale, p.scale, p.scale);
      matrix.setPosition(p.position);
      mesh.setMatrixAt(i, matrix);
      indices[i] = p.idx;
    });
    geometry.setAttribute('aIndex', new THREE.InstancedBufferAttribute(indices, 1));
    mesh.instanceMatrix.needsUpdate = true;
    mesh.name = 'spines';
    mesh.frustumCulled = false;
    this.spineMesh = mesh;
    this.spineCount = placements.length;
    this._disposables.push(geometry);
    this.group.add(mesh);
  }

  /* -- channel-density dots ------------------------------------------ */

  _buildChannelDots() {
    const maxNa = Math.max(this.morph.channel_max?.g_na ?? 0, 1e-9);
    if (maxNa <= 1e-9) return;

    const placements = [];
    for (const section of this.morph.sections || []) {
      const curve = this._curves.get(section.label);
      if (!curve) continue;
      const n = section.comps.length;
      for (let k = 0; k < n; k += 1) {
        const idx = section.comps[k];
        const comp = this.byIndex.get(idx);
        if (!comp || !comp.g_na) continue;
        const density = comp.g_na / maxNa;
        const want = Math.min(14, Math.round(density * 12));
        if (want < 1) continue;
        const random = mulberry32(idx * 3779 + 91);
        const rBase = this._radius(section.radii[k]);
        for (let s = 0; s < want; s += 1) {
          const u = (k + (s + 0.5) / want) / n;
          const uu = Math.min(0.999, Math.max(0.001, u + (random() - 0.5) * 0.02));
          const point = curve.getPointAt(uu);
          const tangent = curve.getTangentAt(uu).normalize();
          let axis = new THREE.Vector3(0, 1, 0);
          if (Math.abs(tangent.dot(axis)) > 0.9) axis = new THREE.Vector3(1, 0, 0);
          const perp = new THREE.Vector3().crossVectors(tangent, axis).normalize();
          const dir = perp.applyAxisAngle(tangent, random() * Math.PI * 2);
          placements.push({
            idx,
            position: point.addScaledVector(dir, rBase * 1.02),
            scale: rBase * 0.16,
          });
        }
      }
    }
    if (!placements.length) return;

    const geometry = new THREE.SphereGeometry(1, 5, 4);
    const material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: /* glsl */`
        attribute float aIndex;
        varying float vCompIdx;
        void main() {
          vCompIdx = aIndex;
          vec4 mvPosition = modelViewMatrix * instanceMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * mvPosition;
        }`,
      fragmentShader: /* glsl */`
        precision highp float;
        uniform sampler2D uState;
        uniform sampler2D uMeta;
        uniform float uDim;
        varying float vCompIdx;
        void main() {
          vec2 uvc = vec2((vCompIdx + 0.5) / ${TEX_W}.0, 0.5);
          vec4 st = texture2D(uState, uvc);
          vec4 mt = texture2D(uMeta, uvc);
          float open = clamp(st.g, 0.0, 1.0);
          vec3 base = mix(vec3(0.25, 0.55, 0.95), vec3(1.0, 0.85, 0.45), open);
          float glow = 0.22 + open * 1.5 + st.a * 1.4;
          gl_FragColor = vec4(base * glow * mix(uDim, 1.0, mt.r), 0.85);
        }`,
    });

    const mesh = new THREE.InstancedMesh(geometry, material, placements.length);
    const indices = new Float32Array(placements.length);
    const matrix = new THREE.Matrix4();
    placements.forEach((p, i) => {
      matrix.makeScale(p.scale, p.scale, p.scale);
      matrix.setPosition(p.position);
      mesh.setMatrixAt(i, matrix);
      indices[i] = p.idx;
    });
    geometry.setAttribute('aIndex', new THREE.InstancedBufferAttribute(indices, 1));
    mesh.instanceMatrix.needsUpdate = true;
    mesh.name = 'channel-dots';
    mesh.frustumCulled = false;
    mesh.renderOrder = 3;
    this.channelDots = mesh;
    this.channelDotCount = placements.length;
    this._materials.push(material);
    this._disposables.push(geometry);
    this.group.add(mesh);
  }

  /* -- axon current-flow particles ----------------------------------- */

  _buildParticles(count = 260) {
    const axon = this.morph.axon;
    if (!axon || !axon.points || axon.points.length < 2) return;

    const path = new THREE.CatmullRomCurve3(axon.points.map((p) => this._v3(p)), false, 'centripetal', 0.5);
    const SAMPLES = 300;
    this._axonLUT = new Float32Array(SAMPLES * 3);
    this._axonComp = new Float32Array(SAMPLES);
    for (let i = 0; i < SAMPLES; i += 1) {
      const point = path.getPointAt(i / (SAMPLES - 1));
      this._axonLUT[i * 3] = point.x;
      this._axonLUT[i * 3 + 1] = point.y;
      this._axonLUT[i * 3 + 2] = point.z;
      const seg = Math.min(axon.idxs.length - 1, Math.floor((i / SAMPLES) * axon.idxs.length));
      this._axonComp[i] = axon.idxs[seg];
    }

    const positions = new Float32Array(count * 3);
    const offsets = new Float32Array(count);
    const brightness = new Float32Array(count);
    for (let i = 0; i < count; i += 1) offsets[i] = i / count;

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('aBright', new THREE.BufferAttribute(brightness, 1));

    const material = new THREE.ShaderMaterial({
      uniforms: { uSize: { value: 26 * (window.devicePixelRatio || 1) } },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: /* glsl */`
        attribute float aBright;
        varying float vBright;
        uniform float uSize;
        void main() {
          vBright = aBright;
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = uSize * (0.35 + aBright) / max(0.001, -mvPosition.z);
          gl_Position = projectionMatrix * mvPosition;
        }`,
      fragmentShader: /* glsl */`
        precision highp float;
        varying float vBright;
        void main() {
          vec2 d = gl_PointCoord - vec2(0.5);
          float r = length(d);
          if (r > 0.5) discard;
          float falloff = smoothstep(0.5, 0.0, r);
          vec3 colour = mix(vec3(0.2, 0.6, 1.0), vec3(1.0, 0.95, 0.7), vBright);
          gl_FragColor = vec4(colour * falloff * (0.15 + vBright * 1.6), falloff * 0.85);
        }`,
    });

    const points = new THREE.Points(geometry, material);
    points.name = 'axon-current';
    points.frustumCulled = false;
    this.particles = points;
    this._particleOffsets = offsets;
    this._particleBright = brightness;
    this._particleCount = count;
    this._materials.push(material);
    this._disposables.push(geometry);
    this.group.add(points);
  }

  /* ================================================================== */
  /* Per-frame updates                                                  */
  /* ================================================================== */

  /**
   * Push one solver frame into the state texture.
   * @param {object} frame  a `state` message from the WebSocket
   */
  updateState(frame) {
    if (!frame || !frame.V_mV) return;
    this.lastFrame = frame;

    const [vmin, vmax] = this.opts.voltageRange;
    const span = Math.max(1e-6, vmax - vmin);
    const V = frame.V_mV;
    const gNa = frame.g_Na_nS;
    const gK = frame.g_K_nS;
    const data = this._stateData;
    const n = Math.min(this.count, V.length);

    if (gNa) {
      let frameMax = 0;
      for (let i = 0; i < n; i += 1) if (gNa[i] > frameMax) frameMax = gNa[i];
      // Auto-range with slow decay so the scale follows the run without flicker.
      this._gNaMax = Math.max(frameMax, this._gNaMax * 0.995, 1e-9);
    }
    if (gK) {
      let frameMax = 0;
      for (let i = 0; i < n; i += 1) if (gK[i] > frameMax) frameMax = gK[i];
      this._gKMax = Math.max(frameMax, this._gKMax * 0.995, 1e-9);
    }

    for (let i = 0; i < n; i += 1) {
      const o = i * 4;
      data[o] = clamp01((V[i] - vmin) / span);
      data[o + 1] = gNa ? clamp01(gNa[i] / this._gNaMax) : 0;
      data[o + 2] = gK ? clamp01(gK[i] / this._gKMax) : 0;
    }

    const spikes = frame.spike_events;
    if (spikes && spikes.length) {
      for (let i = 0; i < spikes.length; i += 1) {
        const idx = spikes[i];
        if (idx >= 0 && idx < this.count) data[idx * 4 + 3] = 1;
      }
    }

    this.stateTexture.needsUpdate = true;
  }

  /** Animation-frame tick: decays spike glow and advances the particles. */
  update(dt, elapsed) {
    const decay = Math.exp(-dt / SPIKE_TAU);
    const data = this._stateData;
    let anyGlow = false;
    for (let i = 0; i < this.count; i += 1) {
      const o = i * 4 + 3;
      if (data[o] > 0.001) {
        data[o] *= decay;
        anyGlow = true;
      } else if (data[o] !== 0) {
        data[o] = 0;
      }
    }
    if (anyGlow) this.stateTexture.needsUpdate = true;

    this.uniforms.uTime.value = elapsed;
    this._updateParticles(dt);
  }

  _updateParticles(dt) {
    if (!this.particles || !this._axonLUT) return;
    const positions = this.particles.geometry.getAttribute('position');
    const bright = this.particles.geometry.getAttribute('aBright');
    const lut = this._axonLUT;
    const samples = this._axonComp.length;
    const state = this._stateData;
    const speed = 0.35;

    for (let i = 0; i < this._particleCount; i += 1) {
      let u = this._particleOffsets[i] + dt * speed;
      if (u > 1) u -= 1;
      this._particleOffsets[i] = u;

      const s = Math.min(samples - 1, Math.floor(u * samples));
      positions.array[i * 3] = lut[s * 3];
      positions.array[i * 3 + 1] = lut[s * 3 + 1];
      positions.array[i * 3 + 2] = lut[s * 3 + 2];

      // Brightness follows the local spike glow, so particles light up only
      // where the solver actually fired.
      const comp = this._axonComp[s];
      const glow = state[comp * 4 + 3];
      const depol = state[comp * 4];
      this._particleBright[i] = clamp01(glow * 1.2 + Math.max(0, depol - 0.55) * 1.4);
    }
    positions.needsUpdate = true;
    bright.needsUpdate = true;
  }

  /* ================================================================== */
  /* Interaction / display state                                        */
  /* ================================================================== */

  /** 0 = voltage, 1 = live g_Na, 2 = live g_K, 3 = static channel density. */
  setMode(mode) {
    this._mode = mode;
    this.uniforms.uMode.value = mode;
  }

  setGlow(value) { this.uniforms.uGlow.value = value; }

  /** Highlight a set of compartment types; pass null/empty to show all. */
  setRegionFilter(types) {
    const active = types && types.length ? new Set(types) : null;
    for (const comp of this.compartments) {
      this._metaData[comp.idx * 4] = !active || active.has(comp.type) ? 1 : 0;
    }
    this.uniforms.uDim.value = active ? 0.13 : 1.0;
    this.metaTexture.needsUpdate = true;
  }

  setSelected(idx) {
    if (this._selected >= 0) this._metaData[this._selected * 4 + 3] = 0;
    this._selected = (idx === null || idx === undefined) ? -1 : idx;
    if (this._selected >= 0) this._metaData[this._selected * 4 + 3] = 1;
    this.metaTexture.needsUpdate = true;
  }

  get selected() { return this._selected; }

  setSpinesVisible(on) { if (this.spineMesh) this.spineMesh.visible = on; }

  setChannelDotsVisible(on) { if (this.channelDots) this.channelDots.visible = on; }

  setParticlesVisible(on) { if (this.particles) this.particles.visible = on; }

  setMyelinVisible(on) { if (this.myelinMesh) this.myelinMesh.visible = on; }

  /** Cutaway: apply clipping planes to every material we own. */
  setClippingPlanes(planes) {
    for (const material of this._materials) {
      material.clippingPlanes = planes;
      material.clipShadows = true;
      material.needsUpdate = true;
    }
  }

  /** Cheap LOD: swap the merged high/low geometry by camera distance. */
  updateLOD(camera, threshold = 26) {
    if (!this.meshHigh || !this.meshLow) return;
    const distance = camera.position.length();
    const useLow = distance > threshold;
    if (this.meshHigh.visible === !useLow) return;
    this.meshHigh.visible = !useLow;
    this.meshLow.visible = useLow;
    if (this.spineMesh) this.spineMesh.visible = !useLow && this.opts.spines;
  }

  /** Raycast hit -> compartment index (-1 when nothing was hit). */
  pick(raycaster) {
    const target = this.meshHigh.visible ? this.meshHigh : this.meshLow;
    const hits = raycaster.intersectObject(target, false);
    if (!hits.length) return -1;
    const attribute = target.geometry.getAttribute('aIndex');
    return Math.round(attribute.getX(hits[0].face.a));
  }

  /** World-space centre of a compartment (for camera focus). */
  centreOf(idx) {
    const comp = this.byIndex.get(idx);
    return comp ? this._v3(comp.c) : null;
  }

  dispose() {
    for (const item of this._disposables) item.dispose?.();
    for (const material of this._materials) material.dispose();
    this.stateTexture.dispose();
    this.metaTexture.dispose();
    this.group.clear();
  }
}

export default NeuronMesh;
