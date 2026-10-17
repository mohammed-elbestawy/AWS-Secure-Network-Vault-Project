import { MAX_PLAINTEXT_BYTES, byteLength, encryptText } from "./crypto.js";
import { $, api, copyText, flashLabel, formatDate, friendlyError, hasWebCrypto, setHidden } from "./common.js";

const form = $("#create-form");
const textarea = $("#secret");
const counter = $("#counter");
const submit = $("#submit");
const errorBox = $("#form-error");
const result = $("#result");
const linkField = $("#link");
const copyButton = $("#copy-link");
const resultMeta = $("#result-meta");
const againButton = $("#create-another");

function showError(message) {
  errorBox.textContent = message;
  setHidden(errorBox, !message);
}

function updateCounter() {
  const bytes = byteLength(textarea.value);
  counter.textContent = `${bytes.toLocaleString()} / ${MAX_PLAINTEXT_BYTES.toLocaleString()} bytes`;
  counter.classList.toggle("over", bytes > MAX_PLAINTEXT_BYTES);
}

if (!hasWebCrypto()) {
  setHidden($("#insecure"), false);
  submit.disabled = true;
}

textarea.addEventListener("input", updateCounter);
updateCounter();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");

  const text = textarea.value;
  if (!text.trim()) return showError("Enter a secret first.");
  if (byteLength(text) > MAX_PLAINTEXT_BYTES) return showError("That secret is too large.");

  submit.disabled = true;
  submit.textContent = "Encrypting...";
  try {
    const { blob, key } = await encryptText(text);
    const response = await api("/api/secrets", {
      method: "POST",
      body: {
        ciphertext: blob,
        ttl: Number($("#ttl").value),
        max_views: Number($("#views").value),
      },
    });
    if (!response.ok) return showError(friendlyError(response.status));

    const link = `${location.origin}/view.html?id=${response.data.id}#${key}`;
    linkField.value = link;
    const views = Number($("#views").value);
    resultMeta.textContent =
      `Opens ${views === 1 ? "once" : `up to ${views} times`}. Expires ${formatDate(response.data.expires_at)}.`;
    textarea.value = "";
    updateCounter();
    setHidden(form, true);
    setHidden(result, false);
    linkField.focus();
    linkField.select();
  } catch (_) {
    showError("Encryption failed in this browser.");
  } finally {
    submit.disabled = false;
    submit.textContent = "Create link";
  }
});

copyButton.addEventListener("click", async () => {
  const ok = await copyText(linkField.value, linkField);
  flashLabel(copyButton, ok ? "Copied" : "Press Ctrl+C");
});

againButton.addEventListener("click", () => {
  linkField.value = "";
  setHidden(result, true);
  setHidden(form, false);
  textarea.focus();
});
