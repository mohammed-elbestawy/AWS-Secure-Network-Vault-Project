import test from "node:test";
import assert from "node:assert/strict";
import {
  MAX_PLAINTEXT_BYTES,
  decryptBlob,
  encryptText,
  fromBase64Url,
  toBase64Url,
} from "../frontend/assets/js/crypto.js";

test("round trip with ascii", async () => {
  const { blob, key } = await encryptText("correct horse battery staple");
  assert.equal(await decryptBlob(blob, key), "correct horse battery staple");
});

test("round trip with arabic, emoji and newlines", async () => {
  const text = "كلمة السر: p@ss\nسطر ٢ \u{1F512}\ttab";
  const { blob, key } = await encryptText(text);
  assert.equal(await decryptBlob(blob, key), text);
});

test("same plaintext never produces the same ciphertext or key", async () => {
  const a = await encryptText("same");
  const b = await encryptText("same");
  assert.notEqual(a.blob, b.blob);
  assert.notEqual(a.key, b.key);
});

test("key is 32 bytes encoded in 43 base64url characters", async () => {
  const { key } = await encryptText("x");
  assert.equal(key.length, 43);
  assert.equal(fromBase64Url(key).length, 32);
});

test("blob only uses the base64url alphabet", async () => {
  const { blob } = await encryptText("alphabet check ".repeat(40));
  assert.match(blob, /^[A-Za-z0-9_-]+$/);
});

test("stored size is padded and hides exact length", async () => {
  const a = await encryptText("a");
  const b = await encryptText("a".repeat(200));
  assert.equal(a.blob.length, b.blob.length);
  const c = await encryptText("a".repeat(500));
  assert.ok(c.blob.length > a.blob.length);
});

test("blob length stays inside the server limits", async () => {
  const small = await encryptText("x");
  const large = await encryptText("x".repeat(MAX_PLAINTEXT_BYTES));
  assert.ok(small.blob.length >= 40);
  assert.ok(large.blob.length <= 7168);
});

test("wrong key fails", async () => {
  const { blob } = await encryptText("secret");
  const other = await encryptText("other");
  await assert.rejects(decryptBlob(blob, other.key));
});

test("tampered ciphertext fails authentication", async () => {
  const { blob, key } = await encryptText("secret");
  const bytes = fromBase64Url(blob);
  bytes[bytes.length - 1] ^= 1;
  await assert.rejects(decryptBlob(toBase64Url(bytes), key));
});

test("rejects empty, oversized and malformed input", async () => {
  await assert.rejects(encryptText(""), /empty/);
  await assert.rejects(encryptText("x".repeat(MAX_PLAINTEXT_BYTES + 1)), /too_long/);
  const { blob, key } = await encryptText("x");
  await assert.rejects(decryptBlob(blob, "short"));
  await assert.rejects(decryptBlob("not base64!", key));
});
