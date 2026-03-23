import { EntropyChart } from "./EntropyChart";

function Stat({ label, value, sub, compact }) {
  return (
    <div style={{ padding: compact ? "12px 14px" : "16px 20px", background: "#FAFAF8", border: "1px solid #E8E4DF", borderRadius: 2 }}>
      <p style={{ fontSize: 9, letterSpacing: "0.15em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: compact ? 4 : 6, fontWeight: 600 }}>{label}</p>
      <p style={{ fontSize: compact ? 20 : 28, fontWeight: 300, color: "#1A1A1A", lineHeight: 1 }}>{value}</p>
      {sub && !compact && <p style={{ fontSize: 10, color: "#BDBDBD", marginTop: 4 }}>{sub}</p>}
    </div>
  );
}

export function OpinionBar({ metrics }) {
  const dominant = metrics?.dominant_opinion;
  const consensus = metrics?.consensus || 0;
  if (!dominant) return null;
  const labels = ["strongly agree", "agree", "neutral", "disagree", "strongly disagree"];
  const colors = ["#1A7F4B", "#6DB88F", "#C8BFB5", "#D4896A", "#C0392B"];
  const idx = { strongly_agree: 0, agree: 1, neutral: 2, disagree: 3, strongly_disagree: 4 };
  const di = idx[dominant] ?? 2;
  const flex = [0.08, 0.15, 0.15, 0.15, 0.08];
  flex[di] = Math.max(consensus, 0.25);
  const total = flex.reduce((a, b) => a + b, 0);
  return (
    <div style={{ marginTop: 16 }}>
      <p style={{ fontSize: 10, color: "#9B9B9B", marginBottom: 8, letterSpacing: "0.05em" }}>
        Dominant: <strong style={{ color: "#1A1A1A" }}>{dominant.replace(/_/g, " ")}</strong>
        <span style={{ marginLeft: 8, color: "#6B6B6B" }}>{(consensus * 100).toFixed(0)}%</span>
      </p>
      <div style={{ display: "flex", height: 6, gap: 2 }}>
        {flex.map((f, i) => (
          <div key={i} style={{ flex: f / total, background: colors[i], borderRadius: 1, transition: "flex 0.5s ease" }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "#BDBDBD", marginTop: 4, letterSpacing: "0.08em", textTransform: "uppercase" }}>
        <span>Agree</span><span>Neutral</span><span>Disagree</span>
      </div>
    </div>
  );
}

export function MetricsDashboard({ currentRound, totalActions, latestMetrics, metricsHistory, budget, status, compact }) {
  const m = latestMetrics || {};
  if (compact) return (
    <div style={{ background: "#FFFFFF", border: "1px solid #E8E4DF", borderRadius: 2, padding: 16 }}>
      <p style={{ fontSize: 9, letterSpacing: "0.15em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 12, fontWeight: 600 }}>Summary</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
        <Stat label="Rounds" value={currentRound || 0} compact />
        <Stat label="Actions" value={totalActions?.toLocaleString() || 0} compact />
        <Stat label="Entropy" value={m.opinion_entropy != null ? m.opinion_entropy.toFixed(3) : "—"} compact />
        <Stat label="Polarization" value={m.polarization_index != null ? (m.polarization_index * 100).toFixed(0) + "%" : "—"} compact />
      </div>
      {budget && <p style={{ fontSize: 11, color: "#6B6B6B" }}>Tokens: {budget.total_tokens?.toLocaleString()} · Est. cost: ${budget.estimated_cost_usd?.toFixed(4)}</p>}
    </div>
  );

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 12 }}>
        <Stat label="Round" value={currentRound || 0} sub={status} />
        <Stat label="Actions" value={totalActions?.toLocaleString() || 0} sub="agent posts" />
        <Stat label="Entropy" value={m.opinion_entropy != null ? m.opinion_entropy.toFixed(3) : "—"} sub="bits · max 2.32" />
        <Stat label="Polarization" value={m.polarization_index != null ? (m.polarization_index * 100).toFixed(0) + "%" : "—"} sub="0 = uniform" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 }}>
        <Stat label="Gini" value={(m.gini ?? m.gini_coefficient) != null ? (m.gini ?? m.gini_coefficient).toFixed(3) : "—"} sub="posting inequality" />
        <Stat label="Velocity" value={m.opinion_velocity != null ? m.opinion_velocity.toFixed(3) : "—"} sub="mean shift / agent" />
        <Stat label="Activity" value={m.activity_rate != null ? (m.activity_rate * 100).toFixed(0) + "%" : "—"} sub="agents acting" />
      </div>

      {status === "running" && !latestMetrics && (
        <div style={{ padding: "32px 0", textAlign: "center", background: "#FAFAF8", border: "1px solid #E8E4DF", borderRadius: 2, marginBottom: 12 }}>
          <div style={{ width: 22, height: 22, border: "2px solid #E8E4DF", borderTopColor: "#1A1A1A", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
          <p style={{ fontSize: 12, color: "#6B6B6B", marginBottom: 4 }}>Generating agents and building context...</p>
          <p style={{ fontSize: 11, color: "#BDBDBD" }}>First round data will appear in a few seconds to minutes depending on your API key</p>
        </div>
      )}

      {metricsHistory?.length > 1 && (
        <div style={{ background: "#FFFFFF", border: "1px solid #E8E4DF", borderRadius: 2, padding: "16px 20px", marginBottom: 12 }}>
          <p style={{ fontSize: 9, letterSpacing: "0.15em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 12, fontWeight: 600 }}>
            Opinion Entropy Over Time
          </p>
          <EntropyChart data={metricsHistory} />
        </div>
      )}

      {m.dominant_opinion && (
        <div style={{ background: "#FFFFFF", border: "1px solid #E8E4DF", borderRadius: 2, padding: "16px 20px", marginBottom: 12 }}>
          <p style={{ fontSize: 9, letterSpacing: "0.15em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 0, fontWeight: 600 }}>
            Opinion Distribution
          </p>
          <OpinionBar metrics={m} />
        </div>
      )}

      {budget && (
        <div style={{ padding: "12px 16px", background: "#FAFAF8", border: "1px solid #E8E4DF", borderRadius: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <p style={{ fontSize: 11, color: "#6B6B6B" }}>
            {budget.total_tokens?.toLocaleString()} tokens used
            {budget.budget_used_pct != null && <span style={{ marginLeft: 8, color: "#BDBDBD" }}>({budget.budget_used_pct}%)</span>}
          </p>
          <p style={{ fontSize: 11, color: "#1A1A1A", fontWeight: 600 }}>${budget.estimated_cost_usd?.toFixed(4)}</p>
        </div>
      )}
    </div>
  );
}