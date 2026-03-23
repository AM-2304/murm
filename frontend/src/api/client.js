import * as mock from './mockData';

const BASE = import.meta.env.VITE_API_URL || "";
const IS_STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === 'true';

async function request(method, path, body) {
  if (IS_STATIC_DEMO) {
    if (path.includes("/api/projects/") && method === "POST") {
      await mock.MOCK_DELAY(800);
      return { id: "demo-project-1" };
    }
    if (path.includes("/build") && method === "POST") {
      await mock.MOCK_DELAY(2000); // Simulate graph extraction
      return { status: "building", project_id: "demo-project-1" };
    }
    if (path.includes("/graph/stats") && method === "GET") {
      return { entities: 7, relations: 7 };
    }
    if (path.includes("/graph") && method === "GET") {
      return mock.MOCK_GRAPH;
    }
    if (path.includes("/api/runs/") && method === "POST") {
      await mock.MOCK_DELAY(500);
      return { id: "demo-run-1" };
    }
    if (path.includes("/metrics") && method === "GET") {
      return mock.MOCK_METRICS;
    }
    if (path.includes("/report") && method === "GET") {
      await mock.MOCK_DELAY(1500);
      return { report_text: mock.MOCK_REPORT };
    }
    if (path.includes("/api/runs/") && method === "GET") {
      return { status: "running", config: { agents: 5, rounds: 2 } };
    }
    return {};
  }

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
  if (IS_STATIC_DEMO) {
    let internalClock = 0;
    let isActive = true;
    
    const playStream = async () => {
      // Stream agent generation sequentially
      for (let i = 0; i < 5; i++) {
        if (!isActive) return;
        onEvent(mock.MOCK_EVENTS[i]);
        await mock.MOCK_DELAY(800);
      }
      
      // Stream the action rounds
      for (let i = 5; i < mock.MOCK_EVENTS.length; i++) {
        if (!isActive) return;
        onEvent(mock.MOCK_EVENTS[i]);
        // Simulate realistic thinking delays between agent posts
        await mock.MOCK_DELAY(1500 + Math.random() * 1500);
      }
    };
    
    playStream();
    
    return () => { isActive = false; };
  }

  const url = `${BASE}/api/stream/${runId}?since=${since}`;
  const es = new EventSource(url);
  es.onmessage = (e) => { try { onEvent(JSON.parse(e.data)); } catch { } };
  es.onerror = () => es.close();
  return () => es.close();
}