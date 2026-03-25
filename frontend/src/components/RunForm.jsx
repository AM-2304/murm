import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

const inp = {
  width: "100%", padding: "10px 12px", fontSize: 13,
  border: "1px solid #E8E4DF", borderRadius: 2,
  background: "#FFFFFF", color: "#1A1A1A", outline: "none",
};
const lbl = {
  display: "block", fontSize: 10, letterSpacing: "0.15em",
  textTransform: "uppercase", color: "#9B9B9B", marginBottom: 6, fontWeight: 600,
};

const DEFAULTS = {
  n_agents: 5, n_rounds: 5, seed: 42, n_sensitivity_seeds: 1,
  environment_type: "forum", opinion_distribution: "normal",
  scenario_description: "", expert_mode: true,
};

function CostBar({ estimate, loading }) {
  if (loading) return (
    <div style={{ padding: "12px 14px", background: "#FAFAF8", border: "1px solid #E8E4DF", borderRadius: 2, marginTop: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 12, height: 12, border: "1.5px solid #E8E4DF", borderTopColor: "#1A1A1A", borderRadius: "50%", animation: "spin 0.7s linear infinite", flexShrink: 0 }} />
        <span style={{ fontSize: 11, color: "#9B9B9B" }}>Calculating...</span>
      </div>
    </div>
  );
  if (!estimate) return null;

  const cost = estimate.estimated_cost_usd || 0;
  const tokens = estimate.estimated_total_tokens || 0;
  const breakdown = estimate.breakdown || {};
  const model = estimate.model || "";

  // Color the cost: green < $0.01, amber < $0.10, red >= $0.10
  const costColor = cost < 0.01 ? "#1A7F4B" : cost < 0.10 ? "#C17D11" : "#C0392B";

  // Bar widths from breakdown
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;
  const barColors = ["#0057B8", "#1A7F4B", "#D4600A", "#6B21A8"];
  const barEntries = Object.entries(breakdown);

  return (
    <div style={{ padding: "12px 14px", background: "#FAFAF8", border: "1px solid #E8E4DF", borderRadius: 2, marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 10, color: "#9B9B9B", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Cost estimate · {model.split("/").pop()}
        </span>
        <span style={{ fontSize: 16, fontWeight: 700, color: costColor, letterSpacing: "-0.02em" }}>
          ${cost < 0.0001 ? "0.0000" : cost.toFixed(4)}
        </span>
      </div>

      {/* Stacked bar */}
      {total > 0 && (
        <div style={{ display: "flex", height: 4, borderRadius: 2, overflow: "hidden", gap: 1, marginBottom: 8 }}>
          {barEntries.map(([k, v], i) => (
            <div key={k} style={{
              flex: v / total, background: barColors[i % barColors.length],
              transition: "flex 0.3s ease",
              minWidth: v > 0 ? 2 : 0,
            }} />
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "3px 16px" }}>
        {barEntries.map(([k, v], i) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: barColors[i % barColors.length], flexShrink: 0 }} />
            <span style={{ fontSize: 9, color: "#9B9B9B", textTransform: "capitalize", flex: 1 }}>
              {k.replace(/_/g, " ")}
            </span>
            <span style={{ fontSize: 9, color: "#6B6B6B", fontFamily: "monospace" }}>
              ${v.toFixed(4)}
            </span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 6, fontSize: 9, color: "#BDBDBD" }}>
        ~{tokens.toLocaleString()} tokens total · {estimate.total_calls} agent calls
      </div>
    </div>
  );
}

export function RunForm({ projectId, onSubmit, disabled }) {
  const [form, setForm] = useState(DEFAULTS);
  const [estimate, setEstimate] = useState(null);
  const [estimating, setEstimating] = useState(false);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  // Debounced live estimate — fires 600ms after last change
  const fetchEstimate = useCallback(async (agents, rounds, seeds) => {
    setEstimating(true);
    try {
      const data = await api.getEstimate(agents, rounds, seeds);
      if (data) setEstimate(data);
    } catch { }
    finally { setEstimating(false); }
  }, []);

  useEffect(() => {
    const { n_agents, n_rounds, n_sensitivity_seeds } = form;
    if (!n_agents || !n_rounds) return;
    const timer = setTimeout(() => {
      fetchEstimate(n_agents, n_rounds, n_sensitivity_seeds);
    }, 600);
    return () => clearTimeout(timer);
  }, [form.n_agents, form.n_rounds, form.n_sensitivity_seeds, fetchEstimate]);

  // Fetch on mount with defaults
  useEffect(() => { fetchEstimate(DEFAULTS.n_agents, DEFAULTS.n_rounds, DEFAULTS.n_sensitivity_seeds); }, []);

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
        {[
          { key: "n_agents", label: "Agents", hint: "5–15 for free tier", min: 1, max: 500 },
          { key: "n_rounds", label: "Rounds", hint: "5–10 to start", min: 1, max: 200 },
          { key: "seed", label: "Random seed", hint: "Controls reproducibility", min: 0, max: 99999 },
          { key: "n_sensitivity_seeds", label: "Sensitivity seeds", hint: "1–3 independent runs", min: 1, max: 5 },
        ].map(f => (
          <div key={f.key} style={{ marginBottom: 16 }}>
            <label style={lbl}>{f.label}</label>
            <input
              type="number" min={f.min} max={f.max}
              value={form[f.key]}
              onChange={e => set(f.key, parseInt(e.target.value) || f.min)}
              style={inp}
            />
            <p style={{ fontSize: 10, color: "#BDBDBD", marginTop: 3 }}>{f.hint}</p>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={lbl}>Environment</label>
        <select value={form.environment_type} onChange={e => set("environment_type", e.target.value)} style={inp}>
          <option value="forum">Forum: chronological feed</option>
          <option value="network">Network: algorithmic feed (echo chambers)</option>
          <option value="town_hall">Town Hall: structured agenda</option>
        </select>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={lbl}>Opinion Distribution</label>
        <select value={form.opinion_distribution} onChange={e => set("opinion_distribution", e.target.value)} style={inp}>
          <option value="normal">Normal: most agents start neutral</option>
          <option value="bimodal">Bimodal: already polarised population</option>
          <option value="power_law">Power law: momentum toward one side</option>
          <option value="uniform">Uniform: equal spread</option>
        </select>
      </div>

      <div style={{ marginBottom: 20 }}>
        <label style={lbl}>Scenario context <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>optional</span></label>
        <textarea
          value={form.scenario_description}
          onChange={e => set("scenario_description", e.target.value)}
          rows={2}
          placeholder="Additional framing injected at round 1..."
          style={{ ...inp, resize: "vertical", lineHeight: 1.55 }}
        />
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }} onClick={() => set("expert_mode", !form.expert_mode)}>
            <div style={{ 
                width: 32, height: 18, borderRadius: 10, background: form.expert_mode ? "#1A1A1A" : "#E8E4DF",
                position: "relative", transition: "background 0.2s"
            }}>
                <div style={{ 
                    width: 14, height: 14, borderRadius: "50%", background: "#FFF",
                    position: "absolute", top: 2, left: form.expert_mode ? 16 : 2,
                    transition: "left 0.2s"
                }} />
            </div>
            <label style={{ ...lbl, marginBottom: 0, cursor: "pointer", color: form.expert_mode ? "#1A1A1A" : "#9B9B9B" }}>
                Expert Analysis Mode
            </label>
        </div>
        <p style={{ fontSize: 9, color: "#BDBDBD", marginTop: 4, marginLeft: 42 }}>
            Uses multi-step reasoning (metrics, trace, graph) for a 10x more detailed prediction report.
        </p>
      </div>

      {/* Live cost estimate: updates as user changes inputs */}
      <CostBar estimate={estimate} loading={estimating} />

      <button type="submit" disabled={disabled} style={{
        width: "100%", marginTop: 16, padding: "13px 0",
        fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase",
        background: disabled ? "#E8E4DF" : "#1A1A1A",
        color: disabled ? "#9B9B9B" : "#FFFFFF",
        border: "none", borderRadius: 2,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background 0.15s",
      }}>
        {disabled ? "Running..." : "Launch Simulation"}
      </button>
    </form>
  );
}