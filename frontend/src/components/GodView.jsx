import { useState } from "react";

export function GodView({ runId, status, onInjected }) {
    const [content, setContent] = useState("");
    const [source, setSource] = useState("Breaking News");
    const [loading, setLoading] = useState(false);
    const [last, setLast] = useState(null);
    const [error, setError] = useState("");

    async function handleInject(e) {
        e.preventDefault();
        if (status === "completed") {
            if (onBranch) onBranch({ content: content.trim(), source: source.trim() || "external" });
            setContent("");
            return;
        }

        setLoading(true); setError("");
        try {
            const res = await fetch(`/api/runs/${runId}/inject`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: content.trim(), source: source.trim() || "external" }),
            });
            if (!res.ok) {
                const d = await res.json().catch(() => ({}));
                throw new Error(d.detail || "Injection failed");
            }
            const data = await res.json();
            setLast({ content: content.trim(), round: data.injected_round });
            setContent("");
            if (onInjected) onInjected(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    const disabled = status !== "running" && status !== "completed";
    const inp = {
        width: "100%", padding: "9px 12px", fontSize: 12,
        border: "1px solid #E8E4DF", borderRadius: 2,
        background: disabled ? "#FAFAF8" : "#FFFFFF", color: "#1A1A1A", outline: "none",
        fontFamily: "inherit",
    };

    return (
        <div>
            <p style={{ fontSize: 11, color: "#6B6B6B", lineHeight: 1.6, marginBottom: 14 }}>
                {status === "completed" 
                    ? "Inject a counterfactual event post-simulation. This will branch an identical parallel universe to compare how agents react compared to the baseline run."
                    : "Inject a breaking news event into the live simulation. Agents will react to it in the next round. This tests counterfactual scenarios in real time."}
            </p>
            <form onSubmit={handleInject}>
                <div style={{ marginBottom: 10 }}>
                    <label style={{ display: "block", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 5, fontWeight: 600 }}>
                        Event content
                    </label>
                    <textarea
                        value={content}
                        onChange={e => setContent(e.target.value)}
                        rows={3}
                        disabled={disabled}
                        placeholder={disabled ? "Event injection unavailable" : "e.g. New study reveals unexpected side effects..."}
                        style={{ ...inp, resize: "vertical", lineHeight: 1.55 }}
                    />
                </div>
                <div style={{ marginBottom: 12 }}>
                    <label style={{ display: "block", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 5, fontWeight: 600 }}>
                        Source label
                    </label>
                    <input
                        value={source}
                        onChange={e => setSource(e.target.value)}
                        disabled={disabled}
                        placeholder="Breaking News"
                        style={inp}
                    />
                </div>
                {error && (
                    <div style={{ marginBottom: 10, fontSize: 11, color: "#C0392B", padding: "8px 12px", background: "#FFF8F8", borderLeft: "3px solid #C0392B", borderRadius: 2 }}>
                        {error}
                    </div>
                )}
                <button type="submit" disabled={disabled || loading || !content.trim()} style={{
                    width: "100%", padding: "11px 0", fontSize: 10, fontWeight: 700,
                    letterSpacing: "0.15em", textTransform: "uppercase",
                    background: disabled || !content.trim() ? "#E8E4DF" : (status === "completed" ? "#6B21A8" : "#C0392B"),
                    color: disabled || !content.trim() ? "#9B9B9B" : "#FFFFFF",
                    border: "none", borderRadius: 2,
                    cursor: disabled || !content.trim() ? "not-allowed" : "pointer",
                }}>
                    {loading ? "Injecting..." : (status === "completed" ? "Branch & Compare Scenario" : "Inject Live Event")}
                </button>
            </form>
            {last && (
                <div style={{ marginTop: 12, padding: "10px 12px", background: "#FFF0F0", borderLeft: "3px solid #C0392B", borderRadius: 2 }}>
                    <div style={{ fontSize: 9, color: "#C0392B", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 3 }}>
                        Injected at Round {last.round}
                    </div>
                    <div style={{ fontSize: 11, color: "#5A2A2A" }}>{last.content}</div>
                </div>
            )}
        </div>
    );
}