// Client-side encryption for the vault. Runs in browsers and in Node (tests).
// Format of the stored blob: base64url( iv[12] || AES-256-GCM( padded plaintext ) )
// Plaintext is length-prefixed and zero-padded to 256 byte blocks so the stored
// size does not reveal the exact length of the secret.

const BUCKET = 256;
const IV_LEN = 12;
const TAG_LEN = 16;
const KEY_LEN = 32;

// 5,000 bytes keeps the request body (about 6.9 KB of JSON) under the 8 KB limit of the
// WAF core rule set (SizeRestrictions_BODY), so a legitimate secret is never blocked.
export const MAX_PLAINTEXT_BYTES = 5000;
export const KEY_B64_LEN = 43;

const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });

export function toBase64Url(bytes) {
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function fromBase64Url(text) {
  if (typeof text !== "string" || !/^[A-Za-z0-9_-]*$/.test(text)) {
    throw new Error("invalid_encoding");
  }
  const padded = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
  const binary = atob(padded);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out;
}

function pad(data) {
  const total = Math.ceil((data.length + 4) / BUCKET) * BUCKET;
  const out = new Uint8Array(total);
  new DataView(out.buffer).setUint32(0, data.length);
  out.set(data, 4);
  return out;
}

function unpad(buffer) {
  const length = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength).getUint32(0);
  if (length > buffer.length - 4) throw new Error("corrupt_payload");
  return buffer.slice(4, 4 + length);
}

export function byteLength(text) {
  return encoder.encode(text).length;
}

export async function encryptText(text) {
  const data = encoder.encode(text);
  if (data.length === 0) throw new Error("empty");
  if (data.length > MAX_PLAINTEXT_BYTES) throw new Error("too_long");

  const key = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
  const iv = crypto.getRandomValues(new Uint8Array(IV_LEN));
  const sealed = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, pad(data)));

  const blob = new Uint8Array(IV_LEN + sealed.length);
  blob.set(iv, 0);
  blob.set(sealed, IV_LEN);
  const rawKey = new Uint8Array(await crypto.subtle.exportKey("raw", key));
  return { blob: toBase64Url(blob), key: toBase64Url(rawKey) };
}

export async function decryptBlob(blobText, keyText) {
  const blob = fromBase64Url(blobText);
  const raw = fromBase64Url(keyText);
  if (raw.length !== KEY_LEN || blob.length < IV_LEN + TAG_LEN) throw new Error("invalid_input");

  const key = await crypto.subtle.importKey("raw", raw, { name: "AES-GCM" }, false, ["decrypt"]);
  const plain = new Uint8Array(
    await crypto.subtle.decrypt({ name: "AES-GCM", iv: blob.slice(0, IV_LEN) }, key, blob.slice(IV_LEN))
  );
  return decoder.decode(unpad(plain));
}
