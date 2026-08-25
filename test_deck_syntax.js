const fs = require('fs');
const html = fs.readFileSync('public/embodied_deck.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/i)[1];
require('vm').runInNewContext(script, {
  window: {},
  URLSearchParams: global.URLSearchParams,
  matchMedia: () => ({ matches: false }),
  document: {
    getElementById: (id) => ({
      style: { setProperty: () => {} },
      classList: { add: () => {}, remove: () => {}, toggle: () => {} },
      appendChild: () => {},
      children: [],
      addEventListener: () => {},
      getContext: () => ({ fillRect: ()=>{}, stroke: ()=>{}, beginPath: ()=>{}, arc: ()=>{}, closePath: ()=>{}, fill: ()=>{}, setTransform: ()=>{}, createImageData: (w,h)=>({data: new Uint8ClampedArray(w*h*4)}) })
    }),
    createElement: (tag) => ({
      style: { setProperty: () => {} },
      querySelector: () => ({ style: { setProperty: () => {} } }),
      appendChild: () => {},
      getContext: () => ({ fillRect: ()=>{}, stroke: ()=>{}, beginPath: ()=>{}, arc: ()=>{}, closePath: ()=>{}, fill: ()=>{}, setTransform: ()=>{}, createImageData: (w,h)=>({data: new Uint8ClampedArray(w*h*4)}) })
    }),
    querySelectorAll: () => []
  },
  location: { protocol: 'http:', host: 'localhost:8088' },
  performance: { now: Date.now },
  requestAnimationFrame: () => {},
  setInterval: () => {},
  setTimeout: () => {},
  WebSocket: class {
    constructor(url) {
      console.log('Mock WebSocket constructed for:', url);
    }
  }
});
console.log('Syntax & Execution check in Node VM PASSED with 0 errors!');
