const STORAGE_KEY = "apcs_diag_events_v1";
const SESSION_KEY = "apcs_diag_session_v1";
const MAX_EVENTS = 200;
const REMOTE_META_NAME = "apcs-analytics-endpoint";
const REMOTE_EVENT_NAMES = new Set([
  "landing_view",
  "quiz_start",
  "quiz_complete",
  "result_view",
  "product_interest",
  "share_click",
  "quiz_restart",
]);

export function getAttribution(search = (typeof window !== "undefined" ? window.location.search : "")) {
  const p = new URLSearchParams(search);
  return {
    source: p.get("utm_source") || p.get("ref") || "direct",
    medium: p.get("utm_medium") || "none",
    campaign: p.get("utm_campaign") || "none",
    content: p.get("utm_content") || "none",
  };
}

function getSessionId() {
  try {
    let id = sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = globalThis.crypto?.randomUUID?.() || `s_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
      sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  } catch {
    return "session-unavailable";
  }
}

function readQueue() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
  catch { return []; }
}

export function getRemoteEndpoint(doc = (typeof document !== "undefined" ? document : null)) {
  const endpoint = doc?.querySelector?.(`meta[name="${REMOTE_META_NAME}"]`)?.content?.trim() || "";
  return endpoint.startsWith("https://") ? endpoint : "";
}

export function buildRemoteEvent(event) {
  if (!event || !REMOTE_EVENT_NAMES.has(event.name)) return null;
  const remote = {
    schemaVersion: "1.0",
    sessionId: event.sessionId,
    name: event.name,
    at: event.at,
    page: event.page,
    source: event.source,
    medium: event.medium,
    campaign: event.campaign,
    content: event.content,
  };

  // Only funnel fields that are useful for aggregate validation are eligible.
  // Individual quiz answers and exact overall scores are intentionally excluded.
  for (const key of ["quizVersion", "totalQuestions", "elapsedSec", "weakest", "productId"]) {
    if (event[key] !== undefined && event[key] !== null) remote[key] = event[key];
  }
  return remote;
}

async function sendRemote(event) {
  const endpoint = getRemoteEndpoint();
  const remote = buildRemoteEvent(event);
  if (!endpoint || !remote || typeof fetch !== "function") return false;
  try {
    await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=UTF-8" },
      body: JSON.stringify(remote),
      keepalive: true,
      credentials: "omit",
      referrerPolicy: "no-referrer",
    });
    return true;
  } catch {
    // Analytics must never break the learning experience.
    return false;
  }
}

export function track(name, payload = {}) {
  const event = {
    name,
    at: new Date().toISOString(),
    sessionId: getSessionId(),
    page: typeof location !== "undefined" ? location.pathname : "unknown",
    ...getAttribution(),
    ...payload,
  };
  const queue = readQueue();
  queue.push(event);
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(queue.slice(-MAX_EVENTS))); } catch {}
  if (typeof window !== "undefined") {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: `apcs_${name}`, ...event });
  }
  void sendRemote(event);
  return event;
}

export function exportEvents() {
  return readQueue();
}

export function clearEvents() {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
}
