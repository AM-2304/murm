import { useState } from "react";

function renderMd(md) {
  if (!md) return [];
  return md.split("\n").map((line, i) => {
    if (line.startsWith("## ")) return <h2 key={i} style={{ fontSize: 14, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#1A1A1A", margin: "28px 0 10px", paddingBottom: 8, borderBottom: "1px solid #E8E4DF" }}>{line.slice(3)}</h2>;
    if (line.startsWith("# ")) return <h1 key={i} style={{ fontSize: 20, fontWeight: 300, color: "#1A1A1A", margin: "0 0 20px", lineHeight: 1.3 }}>{line.slice(2)}</h1>;
    if (line.startsWith("### ")) return <h3 key={i} style={{ fontSize: 13, fontWeight: 700, color: "#1A1A1A", margin: "16px 0 6px" }}>{line.slice(4)}</h3>;
    if (line.startsWith("--")) return <hr key={i} style={{ border: "none", borderTop: "1px solid #E8E4DF", margin: "20px 0" }} />;
    if (line.startsWith("- ")) return (
      <div key={i} style={{ display: "flex", gap: 10, marginBottom: 5, fontSize: 13, lineHeight: 1.7, color: "#2A2A2A" }}>
        <span style={{ color: "#9B9B9B", flexShrink: 0, marginTop: 1 }}>–</span>
        <span>{line.slice(2)}</span>
      </div>
    );
    if (line.trim() === "") return <div key={i} style={{ height: 8 }} />;
    return <p key={i} style={{ fontSize: 13, lineHeight: 1.75, color: "#2A2A2A", margin: "0 0 2px" }}>{line}</p>;
  });
}

export function ReportView({ report, runId }) {
  const [tab, setTab] = useState("formatted");
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(report || "").then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
  }
  function download() {
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([report || ""], { type: "text/markdown" })),
      download: `murm_${runId?.slice(0, 8) || "report"}.md`,
    });
    a.click(); URL.revokeObjectURL(a.href);
  }

  if (!report) return (
    <div style={{ textAlign: "center", padding: "60px 0" }}>
      <div style={{ width: 22, height: 22, border: "2px solid #E8E4DF", borderTopColor: "#1A1A1A", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 20px" }} />
      <p style={{ fontSize: 12, color: "#6B6B6B", marginBottom: 4 }}>Generating report...</p>
      <p style={{ fontSize: 11, color: "#BDBDBD" }}>The analyst is querying simulation data</p>
    </div>
  );

  const tabBtn = (t, label) => (
    <button onClick={() => setTab(t)} style={{
      padding: "0 16px", height: 40, fontSize: 10, letterSpacing: "0.12em",
      textTransform: "uppercase", fontWeight: tab === t ? 700 : 400,
      color: tab === t ? "#1A1A1A" : "#9B9B9B", background: "none", border: "none",
      borderBottom: tab === t ? "2px solid #1A1A1A" : "2px solid transparent",
      cursor: "pointer",
    }}>{label}</button>
  );

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, borderBottom: "1px solid #E8E4DF" }}>
        <div style={{ display: "flex" }}>
          {tabBtn("formatted", "Formatted")}
          {tabBtn("raw", "Markdown")}
        </div>
        <div style={{ display: "flex", gap: 8, paddingBottom: 8 }}>
          <button onClick={copy} style={{ padding: "7px 14px", fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600, background: copied ? "#F0FFF5" : "#FAFAF8", color: copied ? "#1A7F4B" : "#6B6B6B", border: `1px solid ${copied ? "#A8D5B8" : "#E8E4DF"}`, borderRadius: 2, cursor: "pointer" }}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button onClick={download} style={{ padding: "7px 14px", fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 700, background: "#1A1A1A", color: "#FFFFFF", border: "none", borderRadius: 2, cursor: "pointer" }}>
            Download
          </button>
        </div>
      </div>
      {tab === "formatted" && <div style={{ maxHeight: 520, overflowY: "auto" }}>{renderMd(report)}</div>}
      {tab === "raw" && <pre style={{ fontSize: 11, fontFamily: "monospace", background: "#FAFAF8", padding: 16, borderRadius: 2, overflowX: "auto", maxHeight: 520, whiteSpace: "pre-wrap", color: "#2A2A2A", lineHeight: 1.65, border: "1px solid #E8E4DF" }}>{report}</pre>}
    </div>
  );
}