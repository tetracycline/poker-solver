"""Shrink site data for GitHub Pages: drop never-asked rare-line nodes (pr < 0.002, same MIN_PR_Q as app.js), gzip each flop file.
Strategies, EVs, flags of kept nodes are byte-identical -> graded answers unchanged."""
import os as _os
PFDIR = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # <repo>/postflop
ROOTDIR = _os.path.dirname(PFDIR)  # <repo>
import json, glob, gzip, os, shutil, sys
SRC = f'{PFDIR}/site/postflop'; DST = f'{PFDIR}/pages/postflop'
MIN_PR_Q = 0.002
if os.path.exists(DST): shutil.rmtree(DST)
os.makedirs(f'{DST}/data'); shutil.copy(f'{SRC}/index.html', DST); shutil.copy(f'{SRC}/app.js', DST)
idx = json.load(open(f'{SRC}/data/index.json')); raw = gz = 0; kept = drop = 0
for sp, S in idx['spots'].items():
    qc = {}
    os.makedirs(f'{DST}/data/{sp}', exist_ok=True)
    for ent in S['flops']:
        fl = ent[0]; F = json.load(open(f'{SRC}/data/{sp}/{fl}.json'))
        for v in F['v']:
            L = F['v'][v]; K = [n for n in L if n['pr'] >= MIN_PR_Q]; kept += len(K); drop += len(L) - len(K); F['v'][v] = K
        c = {}
        for v in F['v']:
            for n in F['v'][v]:
                c[v + '|' + n['c']] = c.get(v + '|' + n['c'], 0) + 1; qc[v + '|' + n['c']] = qc.get(v + '|' + n['c'], 0) + len(n['w'])
        ent[1] = c
        b = json.dumps(F, separators=(',', ':')).encode(); raw += len(b)
        z = gzip.compress(b, 9, mtime=0); gz += len(z)
        open(f'{DST}/data/{sp}/{fl}.json.gz', 'wb').write(z)
    S['qcount'] = qc
json.dump(idx, open(f'{DST}/data/index.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(f'nodes kept {kept} dropped {drop}; json {raw/1e6:.1f} MB -> gzip {gz/1e6:.1f} MB')
# loader: per-flop files are gzip; DecompressionStream (Chrome 80+/Safari 16.4+/Firefox 113+), fallback fflate (MIT) loaded on demand
shutil.copy(f'{SRC}/fflate.min.js', f'{DST}/fflate.min.js')
A = open(f'{DST}/app.js').read()
OLD = "const p = fetch(`data/${sp}/${fl}.json`).then(r => { if (!r.ok) throw new Error('http ' + r.status); return r.json(); });"
NEW = "const p = fetch(`data/${sp}/${fl}.json.gz`).then(r => { if (!r.ok) throw new Error('http ' + r.status); return gunzipJSON(r); });"
assert OLD in A
A = A.replace(OLD, NEW).replace("async function loadFlop(sp, fl) {", """let FFL = null;
function fflate() { return FFL || (FFL = new Promise((ok, no) => { const s = document.createElement('script'); s.src = 'fflate.min.js'; s.onload = () => ok(window.fflate); s.onerror = no; document.head.appendChild(s); })); }
async function gunzipJSON(r) {
  if (typeof DecompressionStream === 'function') return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).json();
  const buf = new Uint8Array(await r.arrayBuffer()), f = await fflate(); return JSON.parse(f.strFromU8(f.gunzipSync(buf)));
}
async function loadFlop(sp, fl) {""", 1)
A = A.replace("<span class=\"tag\">", "<span class=\"tag\">", 1)
open(f'{DST}/app.js', 'w').write(A)
I = open(f'{DST}/index.html').read().replace('app.js?v=pf1', 'app.js?v=pf2'); open(f'{DST}/index.html', 'w').write(I)
print('loader patched')
