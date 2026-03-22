const BASE = import.meta.env.VITE_API_URL || "";

async function request(method, path, body) {
  const opts = {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  };
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = j.detail || JSON.stringify(j); } catch { }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  createProject: (title, seed_text = "") =>
    request("POST", "/api/projects/", { title, seed_text }),
  listProjects: () => request("GET", "/api/projects/"),
  getProject: (id) => request("GET", `/api/projects/${id}`),
  uploadFile: async (projectId, file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/api/projects/${projectId}/upload`, { method: "POST", body: form });
    if (!res.ok) { const t = await res.text(); throw new Error(t); }
    return res.json();
  },
  buildGraph: (projectId, body = {}) =>
    request("POST", `/api/graph/${projectId}/build`, body),
  getGraph: (projectId) => request("GET", `/api/graph/${projectId}/graph`),
  getGraphStats: (projectId) => request("GET", `/api/graph/${projectId}/graph/stats`),
  searchGraph: (projectId, query) =>
    request("GET", `/api/graph/${projectId}/graph/search?query=${encodeURIComponent(query)}`),
  createRun: (body) => request("POST", "/api/runs/", body),
  getRun: (runId) => request("GET", `/api/runs/${runId}`),
  cancelRun: (runId) => request("POST", `/api/runs/${runId}/cancel`),
  getReport: (runId) => request("GET", `/api/runs/${runId}/report`),
  getMetrics: (runId) => request("GET", `/api/runs/${runId}/metrics`),
  deleteProject: (id) => request("DELETE", `/api/projects/${id}`),
  deleteRun: (id) => request("DELETE", `/api/runs/${id}`),
};

export function openStream(runId, onEvent, since = 0) {
  const url = `${BASE}/api/stream/${runId}?since=${since}`;
  const es = new EventSource(url);
  es.onmessage = (e) => { try { onEvent(JSON.parse(e.data)); } catch { } };
  es.onerror = () => es.close();
  return () => es.close();
}