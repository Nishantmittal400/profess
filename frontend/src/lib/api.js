const runtimeConfig = typeof window !== "undefined" ? window.__APP_CONFIG__ : undefined;
const runtimeBase = runtimeConfig && runtimeConfig.apiBase ? runtimeConfig.apiBase : undefined;
const envBase = typeof import.meta !== "undefined" && import.meta.env ? import.meta.env.VITE_API_BASE : undefined;

let API_BASE = runtimeBase || envBase || "http://127.0.0.1:8000";
export function setApiBase(url) { API_BASE = url; }
export function getApiBase() { return API_BASE; }

export async function processAudio(file) {
  const fd = new FormData();
  fd.append("audio", file);
  const r = await fetch(`${API_BASE}/process`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return await r.json();
}
