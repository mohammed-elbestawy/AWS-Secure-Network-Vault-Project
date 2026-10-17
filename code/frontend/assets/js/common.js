export const $ = (selector, root = document) => root.querySelector(selector);

export function setHidden(element, hidden) {
  if (element) element.hidden = hidden;
}

export function hasWebCrypto() {
  return Boolean(window.isSecureContext && window.crypto && window.crypto.subtle);
}

export async function api(path, { method = "GET", body } = {}) {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
    credentials: "omit",
    referrerPolicy: "no-referrer",
  });
  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    data = null;
  }
  return { ok: response.ok, status: response.status, data };
}

export async function copyText(text, fallbackElement) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_) {
    if (!fallbackElement) return false;
    fallbackElement.focus();
    fallbackElement.select();
    return document.execCommand("copy");
  }
}

export function flashLabel(button, text, ms = 1600) {
  const original = button.textContent;
  button.textContent = text;
  setTimeout(() => {
    button.textContent = original;
  }, ms);
}

export function formatDate(iso) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
}

export function friendlyError(status) {
  if (status === 403 || status === 429) {
    return "The request was blocked or rate limited. Wait a minute and try again.";
  }
  if (status === 413) return "That secret is too large.";
  if (status >= 500) return "The service is unavailable right now. Try again shortly.";
  return "Something went wrong. Check the input and try again.";
}
