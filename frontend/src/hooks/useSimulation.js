import { useState, useEffect, useRef, useCallback } from "react";
import { api, openStream } from "../api/client";

function toStr(e) {
  if (!e) return "";
  if (typeof e === "string") return e;
  if (typeof e === "object") {
    if (e.detail) return String(e.detail);
    if (e.message) return String(e.message);
    try { return JSON.stringify(e); } catch { }
  }
  return String(e);
}

export function useSimulation() {
  const [runId, setRunId] = useState(null);
  const [status, setStatus] = useState("idle");
  const [currentRound, setCurrentRound] = useState(0);
  const [totalActions, setTotalActions] = useState(0);
  const [latestMetrics, setLatestMetrics] = useState(null);
  const [metricsHistory, setMetricsHistory] = useState([]);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const [budget, setBudget] = useState(null);
  const [liveActions, setLiveActions] = useState([]);
  const [agentProfiles, setAgentProfiles] = useState([]);
  const [liveEvents, setLiveEvents] = useState([]);

  const cleanupSSE = useRef(null);
  const pollInterval = useRef(null);
  const runIdRef = useRef(null);  // keep ref in sync so callbacks always see latest

  function stopPolling() {
    if (pollInterval.current) { clearInterval(pollInterval.current); pollInterval.current = null; }
  }

  // Poll the backend run record every 5s as a fallback for when SSE drops
  function startPolling(id) {
    stopPolling();
    pollInterval.current = setInterval(async () => {
      try {
        const run = await api.getRun(id);
        if (run.status === "completed") {
          setStatus("completed");
          stopPolling();
          fetchReport(id);
        } else if (run.status === "failed") {
          setStatus("failed");
          setError(run.error || "Run failed on server");
          stopPolling();
        } else if (run.status === "cancelled") {
          setStatus("cancelled");
          stopPolling();
        }
      } catch { }
    }, 5000);
  }

  const startRun = useCallback(async (runConfig) => {
    setStatus("running");
    setCurrentRound(0);
    setTotalActions(0);
    setLatestMetrics(null);
    setMetricsHistory([]);
    setReport("");
    setError("");
    setBudget(null);
    setLiveActions([]);
    setAgentProfiles([]);
    setLiveEvents([]);
    stopPolling();

    try {
      const result = await api.createRun(runConfig);
      const id = result.run_id;
      setRunId(id);
      runIdRef.current = id;

      // Start polling immediately: SSE is the fast path, polling is the safety net
      startPolling(id);

      cleanupSSE.current = openStream(id, (event) => {
        // Append every event to the live log for the system console
        setLiveEvents(prev => [...prev.slice(-300), event]);

        if (event.type === "round_completed") {
          setCurrentRound(event.payload.round);
          setTotalActions(n => n + (event.payload.actions || 0));
          setLatestMetrics(event.payload.metrics);
          if (event.payload.budget) setBudget(event.payload.budget);
          setMetricsHistory(h => [...h, { round: event.payload.round, ...event.payload.metrics }]);
          if (event.payload.sample_actions?.length) {
            setLiveActions(prev => [...prev.slice(-150), ...event.payload.sample_actions]);
          }

        } else if (event.type === "agents_ready") {
          // Populate the agent roster from the SSE event
          if (event.payload?.profiles?.length) {
            setAgentProfiles(event.payload.profiles);
          }

        } else if (event.type === "event_injected") {
          // Put the injected event natively into the Live Feed
          setLiveActions(prev => [...prev.slice(-150), {
            agent_id: event.payload.source || "System",
            round: event.payload.round,
            action_type: "external_event",
            content: event.payload.content
          }]);

        } else if (event.type === "simulation_ended") {
          // Final metrics snapshot from the simulation
          // Merge so we don't wipe out round-level metrics (e.g. opinion_entropy) with report-level metrics (e.g. final_entropy)
          if (event.payload?.metrics) {
            setLatestMetrics(prev => ({ ...prev, ...event.payload.metrics }));
          }
          if (event.payload?.total_actions) setTotalActions(event.payload.total_actions);
          setStatus(event.payload.status || "completed");
          stopPolling();
          fetchReport(id);

        } else if (event.type === "simulation_failed") {
          setStatus("failed");
          setError(toStr(event.payload?.error) || "Simulation failed");
          stopPolling();

        } else if (event.type === "done") {
          api.getRun(id).then(run => {
            setStatus(run.status);
            if (run.status === "completed") fetchReport(id);
            else if (run.status === "failed") setError(run.error || "Run failed");
          }).catch(() => { });
          stopPolling();
        }
      });

    } catch (err) {
      setStatus("failed");
      setError(toStr(err));
      stopPolling();
    }
  }, []);

  const cancelRun = useCallback(async () => {
    stopPolling();
    if (runIdRef.current) await api.cancelRun(runIdRef.current).catch(() => null);
    setStatus("cancelled");
    if (cleanupSSE.current) { cleanupSSE.current(); cleanupSSE.current = null; }
  }, []);

  // Fetch report with retries: the report is written asynchronously after the run completes
  // so we may need to wait up to 90 seconds for it to appear
  async function fetchReport(id) {
    const MAX_ATTEMPTS = 20;
    const DELAY_MS = 5000;

    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
      try {
        const data = await api.getReport(id);
        if (data?.report && data.report.trim().length > 0) {
          setReport(data.report);
          return;
        }
      } catch (err) {
        // 404 means report not written yet: keep retrying
        if (err.status !== 404) {
          console.warn("Report fetch error:", err);
        }
      }
      await new Promise(r => setTimeout(r, DELAY_MS));
    }
    setError("Report generation timed out. The simulation completed but no report was produced.");
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
      if (cleanupSSE.current) cleanupSSE.current();
    };
  }, []);

  return {
    runId, status, currentRound, totalActions,
    latestMetrics, metricsHistory, report, error, budget,
    liveActions, agentProfiles, liveEvents,
    startRun, cancelRun,
  };
}