import * as mock from './mockData';

const BASE = import.meta.env.VITE_API_URL || "";
const IS_STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === 'true';

let __mockStatus = "completed";

async function request(method, path, body) {
  if (IS_STATIC_DEMO) {
    // -- Project endpoints --
    if (path === "/api/projects/" && method === "GET") {
      return [{
        project_id: "demo-project-1",
        title: "Federal Reserve Rate Decision",
        status: "ready",
        created_at: Math.floor(Date.now() / 1000) - 3600,
        expert_report_summary: `Prediction Target: How will public sentiment shift towards the Fed's competence over the next 30 days?

Simulation Parameters: 5 agents · 5 rounds · Forum environment · Normal opinion distribution · Seed 42

--

### [EXPERT MODE] ANALYTICAL SYNTHESIS

#### Phase 1: Quantitative Metrics Analysis
The simulation showed a steady rise in **Opinion Entropy (1.54 -> 1.91)** and a sharp climb in **Polarization (0.62 -> 0.85)**. Unlike typical convergence models, the discussion of Fed policy acted as a wedge, driving agents into fixed, demographic-bound clusters. The low Gini coefficient (0.10) confirms that this polarization wasn't driven by a few loud voices, but was a broad-based structural divergence across the entire simulated population.

#### Phase 2: Trace & Discourse Analysis
Discourse analysis of the 25 agent actions reveals a "Two Realities" phenomenon. Institutional agents (e.g., Marcus Chen) focused almost exclusively on the **forward-looking signal** of the Dot Plot. In contrast, retail and consumer agents (e.g., Sarah Okonkwo, Elena Vasquez) focused on **historical breach of trust**. The simulation reached a "discursive deadlock" in Round 3, where no further amount of forward-looking data could shift the negative anchors of the consumer-class agents.

#### Phase 3: Graph Grounding
The local knowledge graph correctly identified the **"Interest Rates" -> "Consumers"** connection as a primary pain node. The emergence of the **"Public Sentiment" -> "Federal Reserve"** negative relationship was grounded in the text's own citation of "Core Inflation," reinforcing that agents were correctly utilizing the seed document's factual constraints to justify their emotional shifts.

--

### 1. Direct Prediction`
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

    // -- Graph endpoints --
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

    // -- Run endpoints --
    if (path === "/api/runs/" && method === "POST") {
      __mockStatus = "running";
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
      return { status: __mockStatus, run_id: "demo-run-1", config: { n_agents: 5, n_rounds: 5, expert_mode: true } };
    }
    if (path.includes("/api/runs/") && method === "DELETE") {
      return { ok: true };
    }
    if (path.includes("/interview") && method === "POST") {
        await mock.MOCK_DELAY(1200);
        return {
            responses: {
                "agent_0": "As a retail investor, I find the Fed's stance terrifying. The 'Expert' report is right—we are locked in a different reality than the big banks.",
                "agent_2": "I'm literally counting the days until Q3. If they don't cut now, my employees are gone. The simulation caught my desperation perfectly."
            }
        };
    }
    if (path.includes("/chat") && method === "POST") {
        await mock.MOCK_DELAY(1000);
        return {
            response: "The Expert Report analyzed the trace across all 5 rounds. It concluded that your 'Main Street' agents had a 92% negative anchor that was structurally impossible to shift with just 'Dot Plot' news."
        };
    }

    // Fallback
    return {};
  }

  // -- Real API mode --
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
          __mockStatus = "completed";
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