import { useState } from "react";
import { api } from "../api/client";

export function AgentInterview({ runId }) {
    const [question, setQuestion] = useState("");
    const [agentIds, setAgentIds] = useState("");
    const [responses, setResponses] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function handleSubmit(e) {
        e.preventDefault();
        if (!question.trim()) return;
        setLoading(true); setError(""); setResponses(null);

        try {
            const ids = agentIds.trim()
                ? agentIds.split(",").map(s => s.trim()).filter(Boolean)
                : [];
            const res = await fetch(`/api/runs/${runId}/interview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question, agent_ids: ids }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || "Interview request failed");
            }
            const data = await res.json();
            setResponses(data.responses || {});
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    const inp = {
        width: "100%", padding: "10px 12px", fontSize: 13,
        border: "1px solid #E8E4DF", borderRadius: 2,
        background: "#FFFFFF", color: "#1A1A1A", outline: "none",
    };

    return (
        <div>
            <form onSubmit={handleSubmit} style={{ marginBottom: 20 }}>
                <div style={{ marginBottom: 12 }}>
                    <label style={{ display: "block", fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 6, fontWeight: 600 }}>
                        Question for agents
                    </label>
                    <textarea
                        value={question}
                        onChange={e => setQuestion(e.target.value)}
                        rows={3}
                        placeholder="e.g. How do you feel about the recent announcement? Has your opinion changed?"
                        style={{ ...inp, resize: "vertical", lineHeight: 1.55 }}
                    />
                </div>
                <div style={{ marginBottom: 16 }}>
                    <label style={{ display: "block", fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 6, fontWeight: 600 }}>
                        Agent IDs (optional — leave blank to sample automatically)
                    </label>
                    <input
                        value={agentIds}
                        onChange={e => setAgentIds(e.target.value)}
                        placeholder="agent-id-1, agent-id-2, ..."
                        style={inp}
                    />
                </div>
                {error && (
                    <div style={{ marginBottom: 12, padding: "10px 14px", background: "#FFF8F8", borderLeft: "3px solid #C0392B", borderRadius: 2, fontSize: 12, color: "#C0392B" }}>
                        {error}
                    </div>
                )}
                <button type="submit" disabled={loading || !question.trim()} style={{
                    padding: "11px 24px", fontSize: 11, fontWeight: 700, letterSpacing: "0.15em",
                    textTransform: "uppercase",
                    background: loading || !question.trim() ? "#E8E4DF" : "#1A1A1A",
                    color: loading || !question.trim() ? "#9B9B9B" : "#FFFFFF",
                    border: "none", borderRadius: 2, cursor: loading || !question.trim() ? "not-allowed" : "pointer",
                }}>
                    {loading ? "Interviewing agents..." : "Interview Agents"}
                </button>
            </form>

            {responses && Object.keys(responses).length > 0 && (
                <div>
                    <p style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 12, fontWeight: 600 }}>
                        Agent Responses
                    </p>
                    {Object.entries(responses).map(([agentId, response]) => (
                        <div key={agentId} style={{
                            marginBottom: 12, padding: "14px 16px",
                            background: "#FAFAF8", border: "1px solid #E8E4DF", borderRadius: 2,
                        }}>
                            <div style={{ fontSize: 9, color: "#9B9B9B", letterSpacing: "0.08em", marginBottom: 6, fontFamily: "monospace" }}>
                                {agentId.slice(0, 12)}...
                            </div>
                            <div style={{ fontSize: 13, color: "#2A2A2A", lineHeight: 1.7 }}>
                                {response}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {responses && Object.keys(responses).length === 0 && (
                <div style={{ padding: "20px 0", textAlign: "center", fontSize: 12, color: "#BDBDBD" }}>
                    No responses returned. The agents may not have any relevant trace history.
                </div>
            )}
        </div>
    );
}