const STORAGE_KEY = "apcs_diag_events_v1";
const MAX_EVENTS = 200;

export function getAttribution(search = window.location.search) {
  const p = new URLSearchParams(search);
  return {
    source: p.get("utm_source") || p.get("ref") || "direct",
    medium: p.get("utm_medium") || "none",
    campaign: p.get("utm_campaign") || "none",
    content: p.get("utm_content") || "none",
  };
}

function readQueue() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
  catch { return []; }
}

export function track(name, payload = {}) {
  const event = {
    name,
    at: new Date().toISOString(),
    page: location.pathname,
    ...getAttribution(),
    ...payload,
  };
  const queue = readQueue();
  queue.push(event);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queue.slice(-MAX_EVENTS)));
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({ event: `apcs_${name}`, ...event });
  return event;
}

export function exportEvents() {
  return readQueue();
}

export function clearEvents() {
  localStorage.removeItem(STORAGE_KEY);
}
