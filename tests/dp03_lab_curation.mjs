import assert from 'node:assert/strict';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import { DP03_SLUG, DP03_REVISION, simulateExactItem, curateDp03Iteration } from '../cloudflare/worker/src/lab-curation/dp03-iteration.mjs';
import worker from '../cloudflare/worker/src/index.mjs';

const base = new URL('../cloudflare/recovery/assets-51/public/', import.meta.url);
const asset = fs.readFileSync(new URL(`labs/${DP03_SLUG}.html`, base), 'utf8');
const desc = simulateExactItem(2, 3, 4, 'desc');
const asc = simulateExactItem(2, 3, 4, 'asc');
assert.deepEqual(desc.at(-1).dp, [0, null, 3, null, null]);
assert.deepEqual(asc.at(-1).dp, [0, null, 3, null, 6]);
assert.equal(desc.some(x => x.reused), false);
assert.equal(asc.find(x => x.reused).capacity, 4);
// Independent one-item subset oracle, including negative objective values.
let oracleCases = 0;
for (let w = 1; w <= 4; w++) for (const v of [-3, 0, 5]) for (let cap = w; cap <= 3*w; cap++) {
  const expected = Array(cap + 1).fill(null); expected[0] = 0; expected[w] = Math.max(expected[w] ?? -Infinity, v);
  assert.deepEqual(simulateExactItem(w, v, cap, 'desc').at(-1).dp, expected);
  oracleCases++;
}
const cured = curateDp03Iteration(asset);
assert(cured.includes('降序：0/1') && cured.includes('升序：重用反例'));
assert(!cured.includes('Step 1｜只做一個最小 transition'));
assert(cured.includes(DP03_REVISION));
assert(cured.includes('contentRevision'));
assert(!cured.includes('<script src="/assets/apcs-lab-runtime-v3.js"></script>'));
assert.throws(() => curateDp03Iteration(asset.replace(DP03_SLUG, 'other-lab')), /identity mismatch/);
assert.throws(() => curateDp03Iteration('<html>different template</html>'), /verified v3/);
// Exercise the canonical Worker route with a closed in-memory asset binding.
// Any unexpected outbound request fails, and no Notion/Write keys are supplied.
const beforeFetch = globalThis.fetch;
globalThis.fetch = async () => { throw new Error('No network allowed in curation test'); };
let assetRequests = 0;
const env = { ASSETS: { fetch: async (request) => {
  assetRequests++;
  const path = new URL(request.url).pathname.replace(/^\//, '');
  const file = new URL(path, base);
  const body = fs.readFileSync(file, 'utf8');
  return new Response(request.method === 'HEAD' ? null : body, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', ETag: 'old-static-tag', 'Content-Length': String(Buffer.byteLength(body)) } });
}}};
try {
  const url = `https://local.invalid/learn/dp/knapsack/lab/${DP03_SLUG}`;
  const get = await worker.fetch(new Request(url), env, {});
  assert.equal(get.status, 200); assert.equal(get.headers.get('X-APCS-Lab'), DP03_SLUG);
  assert.equal(get.headers.get('X-APCS-Lab-Content-Revision'), DP03_REVISION);
  assert.equal(get.headers.get('ETag'), null); assert.equal(get.headers.get('Content-Length'), null);
  assert.equal(get.headers.get('Cache-Control'), 'no-store');
  assert((await get.text()).includes('首次非法重用'));
  const head = await worker.fetch(new Request(url, { method: 'HEAD' }), env, {});
  assert.equal(head.status, 200); assert.equal(await head.text(), '');
  const other = await worker.fetch(new Request('https://local.invalid/learn/bin/boundary-search/lab/bin02-first-true'), env, {});
  assert.equal(other.headers.get('X-APCS-Lab-Content-Revision'), null);
  assert.equal(await other.text(), fs.readFileSync(new URL('labs/bin02-first-true.html', base), 'utf8'));
} finally { globalThis.fetch = beforeFetch; }
console.log(JSON.stringify({ status: 'PASS', oracleCases, routeCases: 3, recoveryAssetsModified: false, productionWrites: 0, assetRequests }));
