// Full round trip against a running instance: browser-side crypto + real HTTP API.
// Usage: BASE_URL=http://127.0.0.1:8099 node tests/e2e-local.mjs
import assert from "node:assert/strict";
import { decryptBlob, encryptText } from "../frontend/assets/js/crypto.js";

const base = process.env.BASE_URL || "http://127.0.0.1:8099";
const json = (method, path, body) =>
  fetch(base + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

const secret = "db_password=\u0623\u0628\u062c\u062f-7f3a!";
const { blob, key } = await encryptText(secret);

const created = await json("POST", "/api/secrets", { ciphertext: blob, ttl: 3600, max_views: 1 });
assert.equal(created.status, 201);
const { id } = await created.json();

const status = await json("GET", `/api/secrets/${id}/status`);
assert.equal(status.status, 200);

const revealed = await json("POST", `/api/secrets/${id}/reveal`);
assert.equal(revealed.status, 200);
const data = await revealed.json();
assert.equal(data.ciphertext, blob);
assert.equal(await decryptBlob(data.ciphertext, key), secret);

assert.equal((await json("POST", `/api/secrets/${id}/reveal`)).status, 404);
assert.equal((await json("GET", `/api/secrets/${id}/status`)).status, 404);

const page = await fetch(base + "/view.html");
assert.equal(page.status, 200);
assert.match(page.headers.get("content-security-policy"), /script-src 'self'/);
const html = await page.text();
assert.ok(!/<script(?![^>]*\bsrc=)/i.test(html), "no inline scripts");
assert.ok(!/\sstyle=/i.test(html), "no inline style attributes");

for (const asset of ["/assets/js/crypto.js", "/assets/js/create.js", "/assets/js/view.js", "/assets/js/common.js", "/assets/css/style.css", "/favicon.svg", "/security.html", "/"]) {
  assert.equal((await fetch(base + asset)).status, 200, asset);
}
console.log("e2e ok");
