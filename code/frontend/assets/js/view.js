import { KEY_B64_LEN, decryptBlob } from "./crypto.js";
import { $, api, copyText, flashLabel, formatDate, hasWebCrypto, setHidden } from "./common.js";

const states = ["loading", "invalid", "gone", "ready", "revealed", "failed"];
const params = new URLSearchParams(location.search);
const id = params.get("id") || "";
const key = location.hash.slice(1);

function show(name) {
  for (const state of states) setHidden($(`#state-${state}`), state !== name);
}

async function main() {
  if (!hasWebCrypto()) {
    setHidden($("#insecure"), false);
    return show("invalid");
  }
  if (!/^[A-Za-z0-9_-]{32}$/.test(id) || key.length !== KEY_B64_LEN || !/^[A-Za-z0-9_-]+$/.test(key)) {
    return show("invalid");
  }

  const status = await api(`/api/secrets/${id}/status`);
  if (status.status === 404) return show("gone");
  if (!status.ok) return show("failed");

  const views = status.data.remaining_views;
  $("#ready-meta").textContent =
    `${views === 1 ? "This secret can be opened once." : `This secret can be opened ${views} more times.`} ` +
    `It expires ${formatDate(status.data.expires_at)}.`;
  show("ready");
}

$("#reveal").addEventListener("click", async () => {
  const button = $("#reveal");
  button.disabled = true;
  const response = await api(`/api/secrets/${id}/reveal`, { method: "POST" });
  if (response.status === 404) return show("gone");
  if (!response.ok) {
    button.disabled = false;
    return show("failed");
  }
  try {
    const text = await decryptBlob(response.data.ciphertext, key);
    $("#secret-text").textContent = text;
    $("#revealed-meta").textContent =
      response.data.remaining_views === 0
        ? "This secret has been destroyed on the server. Copy it now."
        : `${response.data.remaining_views} view(s) left.`;
    history.replaceState(null, "", location.pathname);
    show("revealed");
  } catch (_) {
    $("#decrypt-failed").hidden = false;
    show("failed");
  }
});

$("#copy-secret").addEventListener("click", async () => {
  const ok = await copyText($("#secret-text").textContent);
  flashLabel($("#copy-secret"), ok ? "Copied" : "Copy failed");
});

$("#hide-secret").addEventListener("click", () => {
  $("#secret-text").textContent = "";
  $("#revealed-meta").textContent = "Hidden. Open the link again only if views remain.";
  setHidden($("#secret-actions"), true);
});

main().catch(() => show("failed"));
