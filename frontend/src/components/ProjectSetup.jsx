import { useState, useRef } from "react";
import { api } from "../api/client";

const inp = {
  width: "100%", padding: "11px 14px", fontSize: 13,
  border: "1px solid #E8E4DF", borderRadius: 2,
  background: "#FFFFFF", color: "#1A1A1A", outline: "none",
  transition: "border-color 0.15s",
};
const lbl = {
  display: "block", fontSize: 10, letterSpacing: "0.15em",
  textTransform: "uppercase", color: "#9B9B9B", marginBottom: 8, fontWeight: 600,
};

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

export function ProjectSetup({ onReady }) {
  const [phase, setPhase] = useState("form");
  const [title, setTitle] = useState("");
  const [seedText, setSeedText] = useState("");
  const [predQ, setPredQ] = useState("");
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [progressMsg, setProgressMsg] = useState("");
  const [graphStats, setGraphStats] = useState(null);
  const fileRef = useRef(null);

  async function handleBuild(e) {
    e.preventDefault();
    if (!title.trim() || !predQ.trim()) { setError("Title and prediction question are required."); return; }
    setError(""); setPhase("building");
    try {
      setProgressMsg("Creating project...");
      const proj = await api.createProject(title.trim(), seedText);
      const pid = proj.project_id;
      if (files.length > 0) {
        setProgressMsg(`Uploading ${files.length} file${files.length > 1 ? "s" : ""}...`);
        for (const f of files) await api.uploadFile(pid, f);
      }
      setProgressMsg("Extracting knowledge graph — this takes 30–90 seconds...");
      await api.buildGraph(pid, { prediction_question: predQ, topic_hint: title });
      let attempts = 0;
      while (attempts < 120) {
        await delay(2500);
        const p = await api.getProject(pid);
        if (p.status === "ready") {
          const stats = await api.getGraphStats(pid).catch(() => null);
          setGraphStats(stats); setPhase("ready");
          onReady({ projectId: pid, predictionQuestion: predQ, title });
          return;
        } else if (p.status === "error") {
          throw new Error("Graph construction failed. Check your API key and try with shorter seed text.");
        }
        attempts++;
        setProgressMsg(`Extracting... (${Math.round(attempts * 2.5)}s)`);
      }
      throw new Error("Graph build timed out after 5 minutes.");
    } catch (err) {
      setError(typeof err === "string" ? err : err.message || String(err));
      setPhase("error");
    }
  }

  if (phase === "building") return (
    <div style={{ textAlign: "center", padding: "60px 0" }}>
      <div style={{ width: 28, height: 28, border: "2px solid #E8E4DF", borderTopColor: "#1A1A1A", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 24px" }} />
      <p style={{ fontSize: 13, color: "#6B6B6B", marginBottom: 8 }}>{progressMsg}</p>
      <p style={{ fontSize: 11, color: "#BDBDBD", letterSpacing: "0.05em" }}>Do not close this window</p>
    </div>
  );

  if (phase === "ready") return (
    <div style={{ padding: "20px 0", display: "flex", alignItems: "center", gap: 14 }}>
      <div style={{ width: 28, height: 28, background: "#1A1A1A", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", color: "#FFFFFF", fontSize: 13, flexShrink: 0 }}>✓</div>
      <div>
        <p style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A", marginBottom: 2 }}>Knowledge graph ready</p>
        {graphStats && <p style={{ fontSize: 11, color: "#9B9B9B" }}>{graphStats.n_entities} entities · {graphStats.n_relations} relations</p>}
      </div>
    </div>
  );

  return (
    <form onSubmit={handleBuild}>
      <div style={{ marginBottom: 20 }}>
        <label style={lbl}>Project Title *</label>
        <input required value={title} onChange={e => setTitle(e.target.value)}
          placeholder="e.g. AI Regulation Bill 2026"
          style={inp}
          onFocus={e => e.target.style.borderColor = "#1A1A1A"}
          onBlur={e => e.target.style.borderColor = "#E8E4DF"} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={lbl}>Prediction Question *</label>
        <input required value={predQ} onChange={e => setPredQ(e.target.value)}
          placeholder="e.g. How will public sentiment shift over the next 30 days?"
          style={inp}
          onFocus={e => e.target.style.borderColor = "#1A1A1A"}
          onBlur={e => e.target.style.borderColor = "#E8E4DF"} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={lbl}>Seed Text <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}> (optional if uploading a file)</span></label>
        <textarea value={seedText} onChange={e => setSeedText(e.target.value)} rows={6}
          placeholder="Paste your news article, policy document, financial report, or any source material..."
          style={{ ...inp, resize: "vertical", lineHeight: 1.65 }}
          onFocus={e => e.target.style.borderColor = "#1A1A1A"}
          onBlur={e => e.target.style.borderColor = "#E8E4DF"} />
      </div>
      <div style={{ marginBottom: 28 }}>
        <label style={lbl}>Upload Files <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}> PDF, DOCX, TXT</span></label>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" multiple
          onChange={e => setFiles(Array.from(e.target.files))} style={{ display: "none" }} />
        <button type="button" onClick={() => fileRef.current?.click()} style={{
          padding: "10px 18px", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase",
          fontWeight: 600, border: "1px solid #E8E4DF", borderRadius: 2,
          background: "#FFFFFF", color: "#6B6B6B", cursor: "pointer",
        }}>
          Choose files
        </button>
        {files.length > 0 && <span style={{ marginLeft: 12, fontSize: 12, color: "#6B6B6B" }}>{files.map(f => f.name).join(", ")}</span>}
      </div>
      {error && (
        <div style={{ marginBottom: 20, padding: "12px 16px", background: "#FFF8F8", border: "1px solid #F0DADA", borderLeft: "3px solid #C0392B", borderRadius: 2, fontSize: 13, color: "#C0392B" }}>
          {error}
        </div>
      )}
      <button type="submit" style={{
        width: "100%", padding: "14px 0", fontSize: 11, fontWeight: 700,
        letterSpacing: "0.15em", textTransform: "uppercase",
        background: "#1A1A1A", color: "#FFFFFF", border: "none", borderRadius: 2,
        cursor: "pointer", transition: "opacity 0.15s",
      }}>
        Build Knowledge Graph
      </button>
    </form>
  );
}