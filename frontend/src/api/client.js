import * as mock from './mockData';

const BASE = import.meta.env.VITE_API_URL || "";
const IS_STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === 'true';

async function request(method, path, body) {
  if (IS_STATIC_DEMO) {
    // ---- Project endpoints ----
    if (path === "/api/projects/" && method === "GET") {
      return [{
        project_id: "demo-project-1",
        title: "Federal Reserve Rate Decision",
        status: "ready",
        created_at: Math.floor(Date.now() / 1000) - 3600
      }];
    }
    if (path.includes("/api/projects/") && method === "POST") {
      await mock.MOCK_DELAY(600);
      return { project_id: "demo-project-1" };
    }
    if (path.includes("/api/projects/") && method === "GET") {
      return { project_id: "demo-project-1", title: "Federal Reserve Rate Decision", status: "ready" };
    }
    if (path.includes("/api/projects/") && method === "DELETE") {
      return { ok: true };
    }

    // ---- Graph endpoints ----
    if (path.includes("/build") && method === "POST") {
      await mock.MOCK_DELAY(2000);
      return { status: "building", project_id: "demo-project-1" };
    }
    if (path.includes("/graph/stats")) {
      return { n_entities: 7, n_relations: 7 };
    }
    if (path.includes("/graph")) {
      return mock.MOCK_GRAPH;
    }

    // ---- Run endpoints ----
    if (path === "/api/runs/" && method === "POST") {
      await mock.MOCK_DELAY(500);
      return { run_id: "demo-run-1" };
    }
    if (path.includes("/estimate")) {
      return mock.MOCK_COST_ESTIMATE;
    }
    if (path.includes("/metrics")) {
      return mock.MOCK_SSE_EVENTS
        .filter(e => e.type === "round_completed")
        .map(e => ({ round: e.payload.round, ...e.payload.metrics }));
    }
    if (path.includes("/report")) {
      return { report: mock.MOCK_REPORT };
    }
    if (path.includes("/cancel")) {
      return { ok: true };
    }
    if (path.includes("/api/runs/") && method === "GET") {
      return { status: "completed", run_id: "demo-run-1", config: { n_agents: 5, n_rounds: 5 } };
    }
    if (path.includes("/api/runs/") && method === "DELETE") {
      return { ok: true };
    }

    // Fallback
    return {};
  }

  // ---- Real API mode ----
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
    if (IS_STATIC_DEMO) { await mock.MOCK_DELAY(300); return { ok: true }; }
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
  getEstimate: (agents, rounds, seeds) =>
    request("GET", `/api/runs/estimate?agents=${agents}&rounds=${rounds}&seeds=${seeds}`),
};

export function openStream(runId, onEvent, since = 0) {
  if (IS_STATIC_DEMO) {
    let isActive = true;

    const playStream = async () => {
      for (const event of mock.MOCK_SSE_EVENTS) {
        if (!isActive) return;

        // Delay between events to simulate real-time AI processing
        if (event.type === "agents_ready") {
          await mock.MOCK_DELAY(1500);
        } else if (event.type === "round_completed") {
          // Each round takes 3-5 seconds to simulate agent thinking
          const roundDelay = 3000 + Math.random() * 2000;
          await mock.MOCK_DELAY(roundDelay);
        } else if (event.type === "simulation_ended") {
          await mock.MOCK_DELAY(1000);
        }

        if (!isActive) return;
        onEvent(event);
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