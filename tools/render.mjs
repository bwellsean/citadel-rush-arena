// Renders Citadel Rush card faces from the print-and-play kit's Card component.
// Usage: node render.mjs <blobDir> <outDir> [cardName ...]
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/npm-tools/node_modules/playwright');

const [blobDir, outDir, ...only] = process.argv.slice(2);
const here = path.dirname(new URL(import.meta.url).pathname);
fs.mkdirSync(outDir, { recursive: true });

function templateOf(file) {
  const src = fs.readFileSync(path.join(here, file), 'utf8');
  let t = src.match(/<x-dc>([\s\S]*?)<\/x-dc>/)[1];
  return t.replace(/<helmet>[\s\S]*?<\/helmet>/, '');
}
function logicOf(file) {
  const src = fs.readFileSync(path.join(here, file), 'utf8');
  const code = src.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/)[1];
  return new Function('DCLogic', code + '; return Component;')(class { });
}

const cardTpl = templateOf('Card.dc.html');
const Card = logicOf('Card.dc.html');
const backTpl = templateOf('TGCBack.dc.html');
const data = JSON.parse(fs.readFileSync(path.join(here, 'kitdata.json'), 'utf8'));
const names = ['Halcyte', ...data.runners.map((r) => r.name), ...data.supports.map((s) => s.name)];

const fontDir = path.join(here, 'node_modules/@fontsource');
const fonts = [
  ['Lilita One', 'lilita-one/files/lilita-one-latin-400-normal.woff2', 400, 'normal'],
  ['Barlow', 'barlow/files/barlow-latin-400-normal.woff2', 400, 'normal'],
  ['Barlow', 'barlow/files/barlow-latin-400-italic.woff2', 400, 'italic'],
  ['Barlow', 'barlow/files/barlow-latin-600-normal.woff2', 600, 'normal'],
  ['Barlow', 'barlow/files/barlow-latin-700-normal.woff2', 700, 'normal'],
  ['Barlow', 'barlow/files/barlow-latin-700-italic.woff2', 700, 'italic'],
  ['Barlow Condensed', 'barlow-condensed/files/barlow-condensed-latin-700-normal.woff2', 700, 'normal'],
  ['Chakra Petch', 'chakra-petch/files/chakra-petch-latin-600-normal.woff2', 600, 'normal'],
  ['Chakra Petch', 'chakra-petch/files/chakra-petch-latin-700-normal.woff2', 700, 'normal'],
];
const fontCss = fonts.map(([f, p, w, s]) => `@font-face{font-family:"${f}";src:url(/fonts/${p}) format("woff2");font-weight:${w};font-style:${s}}`).join('\n');
const page0 = `<!doctype html><html><head><meta charset="utf-8"><style>${fontCss}
body{margin:0;font-family:"Barlow","Helvetica Neue",sans-serif;color:#141413;background:transparent}</style></head>
<body><template id="t"></template><div id="out" style="display:inline-block"></div></body></html>`;

// Runs in the browser: expands {{lookups}}, <sc-if> and <sc-for> against vals.
function expand({ tpl, vals }) {
  const get = (scope, expr) => {
    expr = expr.trim();
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    if (/^-?\d+(\.\d+)?$/.test(expr)) return Number(expr);
    return expr.split('.').reduce((o, k) => (o == null ? undefined : o[k]), scope);
  };
  const interp = (scope, s) => s.replace(/\{\{([^}]+)\}\}/g, (_, e) => { const v = get(scope, e); return v == null ? '' : String(v); });
  const whole = (scope, s) => { const m = /^\s*\{\{([^}]+)\}\}\s*$/.exec(s || ''); return m ? get(scope, m[1]) : s; };
  const walk = (node, scope, parent) => {
    if (node.nodeType === 3) { parent.appendChild(document.createTextNode(interp(scope, node.nodeValue))); return; }
    if (node.nodeType !== 1) return;
    const tag = node.tagName.toLowerCase();
    if (tag === 'sc-if') {
      if (whole(scope, node.getAttribute('value'))) node.childNodes.forEach((ch) => walk(ch, scope, parent));
      return;
    }
    if (tag === 'sc-for') {
      const list = whole(scope, node.getAttribute('list')) || [];
      const as = node.getAttribute('as');
      list.forEach((item, i) => node.childNodes.forEach((ch) => walk(ch, { ...scope, [as]: item, $index: i }, parent)));
      return;
    }
    const el = node.namespaceURI === 'http://www.w3.org/2000/svg'
      ? document.createElementNS(node.namespaceURI, node.tagName) : document.createElement(node.tagName);
    for (const a of node.attributes) { if (!a.name.startsWith('hint-')) el.setAttribute(a.name, interp(scope, a.value)); }
    node.childNodes.forEach((ch) => walk(ch, scope, el));
    parent.appendChild(el);
  };
  const t = document.getElementById('t');
  t.innerHTML = tpl;
  const out = document.getElementById('out');
  out.innerHTML = '';
  t.content.childNodes.forEach((ch) => walk(ch, vals, out));
  return Promise.all([...out.querySelectorAll('img')].map((im) => im.complete ? 0 : new Promise((r) => { im.onload = im.onerror = r; })))
    .then(() => document.fonts.ready).then(() => true);
}

const blobFiles = Object.fromEntries(fs.readdirSync(blobDir).filter((f) => /^[0-9a-f]{32}\./.test(f)).map((f) => [f.slice(0, 32), f]));
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 900, height: 1200 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
await page.route('http://cards.local/**', (route) => {
  const u = new URL(route.request().url());
  if (u.pathname === '/') return route.fulfill({ contentType: 'text/html', body: page0 });
  if (u.pathname.startsWith('/fonts/')) return route.fulfill({ contentType: 'font/woff2', body: fs.readFileSync(path.join(fontDir, u.pathname.slice(7))) });
  if (u.pathname.startsWith('/_blob/')) {
    const f = blobFiles[u.pathname.slice(7, 39)];
    if (f) return route.fulfill({ contentType: f.endsWith('.png') ? 'image/png' : 'image/jpeg', body: fs.readFileSync(path.join(blobDir, f)) });
  }
  return route.fulfill({ status: 404, body: '' });
});
await page.goto('http://cards.local/');

const W = 750, H = 1050;
const slug = (n) => n.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const todo = only.length ? only : [...names, '__back'];
for (const name of todo) {
  let tpl, vals;
  if (name === '__back') { tpl = backTpl; vals = {}; }
  else { tpl = cardTpl; const c = new Card(); c.props = { cardName: name, cardW: W, cardH: H }; vals = c.renderVals(); }
  await page.evaluate(expand, { tpl, vals });
  const el = await page.$('#out > div');
  const file = path.join(outDir, (name === '__back' ? 'card-back' : slug(name)) + '.png');
  await el.screenshot({ path: file, omitBackground: true });
  process.stdout.write('.');
}
await browser.close();
console.log('\ndone', todo.length);
