import fs from 'fs';
const src = fs.readFileSync(process.argv[2],'utf8');
const code = src.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/)[1];
const body = code.replace(/^[\s\S]*?renderVals\(\)\s*\{/, '').replace(/const pick =[\s\S]*$/, '');
const f = new Function(body + '; return {runners, supports, art};');
const d = f.call({props:{}});
fs.writeFileSync(process.argv[3], JSON.stringify(d,null,1));
console.log(d.runners.length, d.supports.length, Object.keys(d.art).length);
