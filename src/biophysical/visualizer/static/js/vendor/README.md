# Vendoring three.js for offline use

The visualiser loads three.js as **ES modules** through the import map at the
top of `../../templates/index.html`:

```html
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/"
  }
}
</script>
```

## Why not `three.min.js` + `OrbitControls.js`?

The original file layout asked for those two classic script-tag builds. They
no longer exist in a usable form:

* `three.min.js` (the UMD global build) was **removed in r150**. The only
  browser build shipped today is `build/three.module.js`.
* `OrbitControls.js`, `EffectComposer.js`, `RenderPass.js`,
  `UnrealBloomPass.js`, `OutputPass.js` and `RoomEnvironment.js` are all ES
  modules under `examples/jsm/` and `import` from `'three'`. Loading them with
  a plain `<script>` tag fails.

So the app imports the bare specifiers `three` and `three/addons/...`, and the
import map decides where those resolve. Swapping CDN for local is a two-line
edit and touches no application code.

## Going offline

Pin the same version the import map uses (**0.169.0**) so the addons match the
core build. From the repository root:

```bash
cd src/biophysical/visualizer/static/js/vendor

VER=0.169.0
BASE="https://cdn.jsdelivr.net/npm/three@${VER}"

# core
curl -fL -o three.module.js "${BASE}/build/three.module.js"

# the six addons this app imports
mkdir -p addons/controls addons/postprocessing addons/environments addons/shaders
curl -fL -o addons/controls/OrbitControls.js            "${BASE}/examples/jsm/controls/OrbitControls.js"
curl -fL -o addons/postprocessing/EffectComposer.js     "${BASE}/examples/jsm/postprocessing/EffectComposer.js"
curl -fL -o addons/postprocessing/RenderPass.js         "${BASE}/examples/jsm/postprocessing/RenderPass.js"
curl -fL -o addons/postprocessing/UnrealBloomPass.js    "${BASE}/examples/jsm/postprocessing/UnrealBloomPass.js"
curl -fL -o addons/postprocessing/OutputPass.js         "${BASE}/examples/jsm/postprocessing/OutputPass.js"
curl -fL -o addons/environments/RoomEnvironment.js      "${BASE}/examples/jsm/environments/RoomEnvironment.js"

# transitive imports of the passes above
curl -fL -o addons/postprocessing/Pass.js               "${BASE}/examples/jsm/postprocessing/Pass.js"
curl -fL -o addons/postprocessing/ShaderPass.js         "${BASE}/examples/jsm/postprocessing/ShaderPass.js"
curl -fL -o addons/postprocessing/MaskPass.js           "${BASE}/examples/jsm/postprocessing/MaskPass.js"
curl -fL -o addons/shaders/CopyShader.js                "${BASE}/examples/jsm/shaders/CopyShader.js"
curl -fL -o addons/shaders/LuminosityHighPassShader.js  "${BASE}/examples/jsm/shaders/LuminosityHighPassShader.js"
curl -fL -o addons/shaders/OutputShader.js              "${BASE}/examples/jsm/shaders/OutputShader.js"
```

Or, equivalently, `npm pack three@0.169.0` and copy `build/` and
`examples/jsm/` out of the tarball.

Then edit the import map in `templates/index.html` to:

```json
{
  "imports": {
    "three": "/static/js/vendor/three.module.js",
    "three/addons/": "/static/js/vendor/addons/"
  }
}
```

The trailing slash on `three/addons/` matters - it is a prefix mapping, so
`three/addons/controls/OrbitControls.js` resolves to
`/static/js/vendor/addons/controls/OrbitControls.js`.

Restart is not required; `server.py` mounts `static/` directly, so a browser
reload picks the new files up.

## Checking it worked

Open the visualiser with DevTools on the Network tab and confirm no request
goes to `cdn.jsdelivr.net`. `window.genesis` in the console gives you the live
app object (`genesis.neuron`, `genesis.socket`, `genesis.morph`) for poking at
the scene.

## Version notes

If you move off 0.169.0, keep these in mind:

* `OutputPass` needs **r152+**.
* `new RoomEnvironment()` takes no renderer argument from **r151**; earlier
  versions require `new RoomEnvironment(renderer)`.
* `neuron.js` patches `MeshPhysicalMaterial` through `onBeforeCompile`, hooking
  the `<common>`, `<begin_vertex>`, `<color_fragment>` and
  `<emissivemap_fragment>` chunks. Those chunk names have been stable for a
  long time, but a major refactor of the shader library (for example the
  WebGPU/TSL migration) would be the thing to check first if the cell renders
  plain white.
