let API_BASE = "http://127.0.0.1:8000";
export function setApiBase(url) { API_BASE = url; }
export function getApiBase() { return API_BASE; }

export async function processAudio(file) {
  const fd = new FormData();
  fd.append("audio", file);
  const r = await fetch(`${API_BASE}/process`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return await r.json();
}
