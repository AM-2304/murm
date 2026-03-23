import { useState, useEffect } from "react";
import { ProjectSetup } from "./components/ProjectSetup";
import { GraphPanel } from "./components/GraphPanel";
import { RunForm } from "./components/RunForm";
import { MetricsDashboard } from "./components/MetricsDashboard";
import { ReportView } from "./components/ReportView";
import { AgentFeed } from "./components/AgentFeed";
import { AgentRoster } from "./components/AgentRoster";
import { DeepInteraction } from "./components/DeepInteraction";
import { GodView } from "./components/GodView";
import { ProjectHistory } from "./components/ProjectHistory";
import { SimConsole } from "./components/SimConsole";
import { useSimulation } from "./hooks/useSimulation";
import { api } from "./api/client";

const STEPS = ["Setup", "Graph", "Simulate", "Report"];

function NavBar({ step, setStep, projectTitle, onHistoryClick, showingHistory }) {
  return (
    <nav style={{
      borderBottom: "1px solid #E8E4DF", background: "#FFFFFF",
      display: "flex", alignItems: "center", padding: "0 32px",
      height: 56, position: "sticky", top: 0, zIndex: 50,
    }}>
      <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.2em", color: "#1A1A1A", marginRight: 40, textTransform: "uppercase" }}>
        MURM
      </span>
      <div style={{ display: "flex" }}>
        {STEPS.map((label, i) => (
          <button key={i} onClick={() => i <= step && setStep(i)} style={{
            padding: "0 18px", height: 56, fontSize: 11, letterSpacing: "0.12em",
            textTransform: "uppercase", fontWeight: i === step ? 700 : 400,
            color: i === step ? "#1A1A1A" : i < step ? "#6B6B6B" : "#BDBDBD",
            background: "none", border: "none",
            borderBottom: i === step ? "2px solid #1A1A1A" : "2px solid transparent",
            cursor: i <= step ? "pointer" : "default",
          }}>
            {label}
          </button>
        ))}
      </div>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 16 }}>
        {projectTitle && (
          <span style={{ fontSize: 11, color: "#9B9B9B", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {projectTitle}
          </span>
        )}
        <button onClick={onHistoryClick} style={{
          padding: "7px 14px", fontSize: 10, fontWeight: 600, letterSpacing: "0.12em",
          textTransform: "uppercase", background: showingHistory ? "#1A1A1A" : "none",
          color: showingHistory ? "#FFFFFF" : "#6B6B6B",
          border: "1px solid #E8E4DF", borderRadius: 2, cursor: "pointer",
        }}>
          History
        </button>
        <a href="https://github.com/AM-2304/murm" target="_blank" rel="noreferrer" style={{
          display: "flex", alignItems: "center", gap: 6, textDecoration: "none",
          padding: "7px 14px", fontSize: 10, fontWeight: 600, letterSpacing: "0.12em",
          textTransform: "uppercase", background: "none", color: "#1A1A1A",
          border: "1px solid #E8E4DF", borderRadius: 2, cursor: "pointer",
        }}>
          <svg style={{ width: 14, height: 14 }} fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
          </svg>
          Star Repo
        </a>
      </div>
    </nav>
  );
}

function SectionHead({ label, sub }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <p style={{ fontSize: 10, letterSpacing: "0.15em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 6, fontWeight: 600 }}>{label}</p>
      {sub && <h2 style={{ fontSize: 20, fontWeight: 300, color: "#1A1A1A", lineHeight: 1.3 }}>{sub}</h2>}
    </div>
  );
}

function Card({ children, title, action, style }) {
  return (
    <div style={{ background: "#FFFFFF", border: "1px solid #E8E4DF", borderRadius: 2, ...style }}>
      {(title || action) && (
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #E8E4DF", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          {title && <p style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", fontWeight: 600 }}>{title}</p>}
          {action}
        </div>
      )}
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  );
}

function TabBar({ tabs, active, onChange }) {
  return (
    <div style={{ display: "flex", borderBottom: "1px solid #E8E4DF", marginBottom: 20 }}>
      {tabs.map(t => (
        <button key={t.key} onClick={() => onChange(t.key)} style={{
          padding: "10px 20px", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase",
          fontWeight: active === t.key ? 700 : 400,
          color: active === t.key ? "#1A1A1A" : "#9B9B9B",
          background: "none", border: "none",
          borderBottom: active === t.key ? "2px solid #1A1A1A" : "2px solid transparent",
          marginBottom: -1, cursor: "pointer",
        }}>{t.label}</button>
      ))}
    </div>
  );
}

export default function App() {
  const [step, setStep] = useState(0);
  const [project, setProject] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [simTab, setSimTab] = useState("metrics");
  const [reportTab, setReportTab] = useState("report");
  const [runConfig, setRunConfig] = useState(null);
  const [autoAdvanced, setAutoAdvanced] = useState(false);

  const sim = useSimulation();

  useEffect(() => {
    if (sim.status === "completed" && step === 2 && sim.report && !autoAdvanced) {
      setAutoAdvanced(true);
      setTimeout(() => setStep(3), 500);
    }
  }, [sim.status, sim.report, step, autoAdvanced]);

  // Poll for updated graph data while a run is active (catches new entities added during build)
  useEffect(() => {
    if (sim.status !== "running" || !project?.projectId) return;
    const interval = setInterval(async () => {
      const g = await api.getGraph(project.projectId).catch(() => null);
      if (g) setGraphData(g);
    }, 15000);
    return () => clearInterval(interval);
  }, [sim.status, project?.projectId]);

  async function handleProjectReady({ projectId, predictionQuestion, title }) {
    setProject({ projectId, predictionQuestion, title });
    const graph = await api.getGraph(projectId).catch(() => null);
    setGraphData(graph);
    setStep(1);
    setShowHistory(false);
  }

  async function handleHistorySelect(p) {
    setShowHistory(false);
    const graph = await api.getGraph(p.project_id).catch(() => null);
    setGraphData(graph);
    setProject({ projectId: p.project_id, predictionQuestion: "", title: p.title });
    setStep(1);
  }

  async function handleRunSubmit(config) {
    setRunConfig(config);
    setAutoAdvanced(false);
    setStep(2);
    setSimTab("metrics");
    await sim.startRun({
      ...config,
      project_id: project.projectId,
      prediction_question: project.predictionQuestion,
    });
  }

  function handleBranch(injection) {
    if (!runConfig) return;
    const newConfig = {
      ...runConfig,
      counterfactual_events: [
        ...(runConfig.counterfactual_events || []),
        { round: 1, content: injection.content, source: injection.source }
      ]
    };
    handleRunSubmit(newConfig);
  }

  const errMsg = typeof sim.error === "string" ? sim.error : "";

  return (
    <div style={{ minHeight: "100vh", background: "#F8F6F3", fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif" }}>
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        button, input, textarea, select { font-family: inherit; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadein { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes fadeRow { from { opacity: 0; } to { opacity: 1; } }
        .page { animation: fadein 0.2s ease; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: #D0C8C0; border-radius: 2px; }
      `}</style>

      <NavBar
        step={step} setStep={setStep}
        projectTitle={project?.title}
        onHistoryClick={() => setShowHistory(h => !h)}
        showingHistory={showHistory}
      />

      {/* HISTORY DRAWER */}
      {showHistory && (
        <div style={{
          position: "sticky", top: 56, zIndex: 40,
          background: "#FFFFFF", border: "1px solid #E8E4DF",
          borderTop: "none", maxHeight: 360, overflowY: "auto",
          boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
        }}>
          <div style={{ padding: "12px 24px", borderBottom: "1px solid #E8E4DF" }}>
            <p style={{ fontSize: 10, letterSpacing: "0.15em", textTransform: "uppercase", color: "#9B9B9B", fontWeight: 600 }}>
              Previous Projects
            </p>
          </div>
          <ProjectHistory onSelect={handleHistorySelect} currentProjectId={project?.projectId} />
        </div>
      )}

      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 32px" }}>

        {/* SETUP */}
        {step === 0 && (
          <div className="page" style={{ maxWidth: 580, margin: "0 auto" }}>
            <div style={{ marginBottom: 48 }}>
              <p style={{ fontSize: 10, letterSpacing: "0.2em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 16 }}>
                Swarm Intelligence · Prediction Engine
              </p>
              <h1 style={{ fontSize: 38, fontWeight: 300, color: "#1A1A1A", lineHeight: 1.15, marginBottom: 20 }}>
                Predict how crowds<br />respond to anything.
              </h1>
              <p style={{ fontSize: 14, color: "#6B6B6B", lineHeight: 1.8, maxWidth: 440 }}>
                Feed in any document. Ask a question. A diverse population of autonomous agents debates it across multiple rounds. You receive a calibrated prediction with confidence bounds and full agent-level evidence.
              </p>
            </div>
            <div style={{ background: "#FFFFFF", border: "1px solid #E8E4DF", borderRadius: 2, padding: 28 }}>
              <p style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 20, fontWeight: 600 }}>
                New Prediction Project
              </p>
              <ProjectSetup onReady={handleProjectReady} />
            </div>
          </div>
        )}

        {/* GRAPH & CONFIG */}
        {step === 1 && (
          <div className="page">
            <SectionHead label="Knowledge Graph Ready — Configure Your Run" sub={project?.predictionQuestion} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 20 }}>
              <div>
                <Card title={`Entity Graph${graphData ? ` · ${graphData.nodes?.length || 0} entities · ${(graphData.edges || graphData.links || []).length} edges` : ""}`} style={{ marginBottom: 16 }}>
                  {graphData
                    ? <GraphPanel graphData={graphData} height={440} liveActions={sim.liveActions} />
                    : <div style={{ height: 440, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <div style={{ textAlign: "center", color: "#9B9B9B" }}>
                        <div style={{ width: 24, height: 24, border: "2px solid #E8E4DF", borderTopColor: "#1A1A1A", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 12px" }} />
                        <p style={{ fontSize: 12 }}>Loading graph...</p>
                      </div>
                    </div>
                  }
                </Card>
              </div>
              <Card title="Simulation Parameters">
                <RunForm
                  projectId={project?.projectId}
                  onSubmit={handleRunSubmit}
                  disabled={sim.status === "running"}
                />
              </Card>
            </div>
          </div>
        )}

        {/* SIMULATE */}
        {step === 2 && (
          <div className="page">
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 28 }}>
              <SectionHead
                label={sim.status === "running" ? "Simulation Running" : sim.status === "failed" ? "Run Failed" : "Simulation Complete"}
                sub={project?.predictionQuestion}
              />
              <div style={{ display: "flex", gap: 10, paddingTop: 4 }}>
                {sim.status === "completed" && sim.report && (
                  <button onClick={() => setStep(3)} style={{
                    padding: "10px 22px", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em",
                    textTransform: "uppercase", background: "#1A1A1A", color: "#FFFFFF",
                    border: "none", borderRadius: 2, cursor: "pointer",
                  }}>
                    View Report
                  </button>
                )}
                {sim.status === "completed" && !sim.report && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 0" }}>
                    <div style={{ width: 14, height: 14, border: "2px solid #E8E4DF", borderTopColor: "#1A1A1A", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                    <span style={{ fontSize: 12, color: "#6B6B6B" }}>Generating report...</span>
                  </div>
                )}
                {sim.status === "running" && (
                  <button onClick={sim.cancelRun} style={{
                    padding: "10px 22px", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em",
                    textTransform: "uppercase", background: "none", color: "#C0392B",
                    border: "1px solid #C0392B", borderRadius: 2, cursor: "pointer",
                  }}>
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {/* LIVE COMMAND CENTER GRID */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: 20 }}>
              
              {/* LEFT COLUMN: Evolving Graph & Console */}
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                <Card title="Evolving Knowledge Graph" style={{ flex: 1, minHeight: 480 }}>
                  {graphData 
                    ? <GraphPanel graphData={graphData} height={440} liveActions={sim.liveActions} />
                    : <div style={{ height: 440, display: "flex", alignItems: "center", justifyContent: "center", color: "#BDBDBD", fontSize: 12 }}>Waiting for graph...</div>}
                </Card>
                <SimConsole events={sim.liveEvents || []} />
              </div>

              {/* RIGHT COLUMN: Feed, Metrics, God Mode */}
              <div style={{ display: "flex", flexDirection: "column", gap: 20, height: 740 }}>
                
                {/* Live Stream Panel */}
                <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
                  <TabBar
                    tabs={[
                      { key: "feed", label: "Live Stream" },
                      { key: "metrics", label: "Metrics" },
                      { key: "agents", label: "Agent Roster" },
                      { key: "god", label: "God Mode" },
                    ]}
                    active={simTab}
                    onChange={setSimTab}
                  />
                  <div style={{ overflowY: "auto", flex: 1 }}>
                    {simTab === "feed" && (
                      <AgentFeed actions={sim.liveActions || []} status={sim.status} />
                    )}
                    {simTab === "metrics" && (
                      <MetricsDashboard
                        currentRound={sim.currentRound}
                        totalActions={sim.totalActions}
                        latestMetrics={sim.latestMetrics}
                        metricsHistory={sim.metricsHistory}
                        budget={sim.budget}
                        status={sim.status}
                      />
                    )}
                    {simTab === "agents" && (
                      <Card>
                        <AgentRoster agents={sim.agentProfiles || []} />
                      </Card>
                    )}
                    {simTab === "god" && (
                      <Card>
                        <GodView runId={sim.runId} status={sim.status} onInjected={() => setSimTab("feed")} onBranch={handleBranch} />
                      </Card>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {errMsg && (
              <div style={{
                marginTop: 20, padding: "16px 20px",
                background: "#FFF8F8", borderLeft: "3px solid #C0392B", borderRadius: 2,
                fontSize: 13, color: "#C0392B", lineHeight: 1.6,
              }}>
                <strong>Run failed:</strong> {errMsg}
                <button onClick={() => setStep(1)} style={{
                  marginLeft: 16, fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase",
                  fontWeight: 600, color: "#1A1A1A", background: "none",
                  border: "1px solid #D0C8C0", borderRadius: 2, padding: "6px 12px", cursor: "pointer",
                }}>
                  Back to settings
                </button>
              </div>
            )}
          </div>
        )}

        {/* REPORT */}
        {step === 3 && (
          <div className="page" style={{ position: "relative" }}>
            <div style={{ position: "absolute", right: 0, top: 0 }}>
              <button onClick={() => setStep(2)} style={{
                padding: "8px 16px", fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase",
                background: "#E8E4DF", color: "#1A1A1A", border: "none", borderRadius: 2, cursor: "pointer", fontWeight: 700
              }}>
                ← Back to Dashboard
              </button>
            </div>
            <SectionHead label="Prediction Report" sub={project?.predictionQuestion} />

            <TabBar
              tabs={[
                { key: "report", label: "Report" },
                { key: "metrics", label: "Metrics" },
                { key: "interview", label: "Interview Agents" },
              ]}
              active={reportTab}
              onChange={setReportTab}
            />

            {reportTab === "report" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 20 }}>
                <div style={{ background: "#FFFFFF", border: "1px solid #E8E4DF", borderRadius: 2, padding: 28 }}>
                  <ReportView report={sim.report} runId={sim.runId} />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <MetricsDashboard
                    currentRound={sim.currentRound}
                    totalActions={sim.totalActions}
                    latestMetrics={sim.latestMetrics}
                    metricsHistory={[]}
                    budget={sim.budget}
                    status={sim.status}
                    compact
                  />
                  <button onClick={() => setStep(1)} style={{
                    width: "100%", padding: "13px 0", fontSize: 11, fontWeight: 700,
                    letterSpacing: "0.15em", textTransform: "uppercase",
                    background: "#1A1A1A", color: "#FFFFFF", border: "none", borderRadius: 2, cursor: "pointer",
                  }}>
                    Run Again
                  </button>
                  <button onClick={() => { setProject(null); setGraphData(null); setStep(0); }} style={{
                    width: "100%", padding: "13px 0", fontSize: 11, fontWeight: 600,
                    letterSpacing: "0.15em", textTransform: "uppercase",
                    background: "none", color: "#6B6B6B", border: "1px solid #E8E4DF", borderRadius: 2, cursor: "pointer",
                  }}>
                    New Project
                  </button>
                </div>
              </div>
            )}

            {reportTab === "metrics" && (
              <MetricsDashboard
                currentRound={sim.currentRound}
                totalActions={sim.totalActions}
                latestMetrics={sim.latestMetrics}
                metricsHistory={sim.metricsHistory}
                budget={sim.budget}
                status={sim.status}
              />
            )}

            {reportTab === "interview" && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                <Card title="Agent Interviews">
                  <p style={{ fontSize: 11, color: "#6B6B6B", marginBottom: 16, lineHeight: 1.5 }}>
                    Ask agents questions. They respond in character based on their trace logic.
                  </p>
                  <DeepInteraction runId={sim.runId} mode="agent" />
                </Card>
                <Card title="Analyst Chat">
                  <p style={{ fontSize: 11, color: "#6B6B6B", marginBottom: 16, lineHeight: 1.5 }}>
                    Ask the Meta-Analyst about causality, significance, or evidence in the report.
                  </p>
                  <DeepInteraction runId={sim.runId} mode="analyst" />
                </Card>
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
}