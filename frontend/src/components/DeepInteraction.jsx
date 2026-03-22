import { useState, useRef, useEffect } from "react";

function Message({ role, content }) {
    const isUser = role === "user";
    return (
        <div style={{
            display: "flex", justifyContent: isUser ? "flex-end" : "flex-start",
            marginBottom: 12,
        }}>
            <div style={{
                maxWidth: "80%", padding: "10px 14px",
                background: isUser ? "#1A1A1A" : "#F5F3EF",
                color: isUser ? "#FFFFFF" : "#1A1A1A",
                borderRadius: 2, fontSize: 13, lineHeight: 1.65,
            }}>
                {content}
            </div>
        </div>
    );
}

export function DeepInteraction({ runId, mode }) {
    const [history, setHistory] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [agentIds, setAgentIds] = useState("");
    const endRef = useRef(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history]);

    const endpoint = mode === "agent"
        ? `/api/runs/${runId}/interview`
        : `/api/runs/${runId}/chat`;

    async function handleSend(e) {
        e.preventDefault();
        const text = input.trim();
        if (!text || loading) return;

        const userMsg = { role: "user", content: text };
        setHistory(h => [...h, userMsg]);
        setInput(""); setLoading(true);

        try {
            let body, res;
            if (mode === "agent") {
                body = {
                    question: text,
                    agent_ids: agentIds.split(",").map(s => s.trim()).filter(Boolean),
                };
                res = await fetch(endpoint, {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body),
                });
                const data = await res.json();
                const responses = data.responses || {};
                if (Object.keys(responses).length === 0) {
                    setHistory(h => [...h, { role: "assistant", content: "No agent responses returned. The trace may be empty." }]);
                } else {
                    for (const [aid, answer] of Object.entries(responses)) {
                        setHistory(h => [...h, {
                            role: "assistant",
                            content: `[${aid.slice(0, 8)}...]\n${answer}`,
                        }]);
                    }
                }
            } else {
                body = { message: text, history: history.slice(-8) };
                res = await fetch(endpoint, {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body),
                });
                const data = await res.json();
                setHistory(h => [...h, { role: "assistant", content: data.response || "(no response)" }]);
            }
        } catch (err) {
            setHistory(h => [...h, { role: "assistant", content: `Error: ${err.message}` }]);
        } finally {
            setLoading(false);
        }
    }

    const placeholder = mode === "agent"
        ? "Ask the agents a question..."
        : "Ask the analyst about the simulation results...";

    return (
        <div style={{ display: "flex", flexDirection: "column", height: 500 }}>
            {mode === "agent" && (
                <div style={{ marginBottom: 12 }}>
                    <label style={{ display: "block", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: "#9B9B9B", marginBottom: 5, fontWeight: 600 }}>
                        Agent IDs (optional — leave blank to auto-sample 5)
                    </label>
                    <input
                        value={agentIds}
                        onChange={e => setAgentIds(e.target.value)}
                        placeholder="agent-id-1, agent-id-2, ..."
                        style={{ width: "100%", padding: "9px 12px", fontSize: 12, border: "1px solid #E8E4DF", borderRadius: 2, background: "#FFFFFF", color: "#1A1A1A", outline: "none", fontFamily: "inherit" }}
                    />
                </div>
            )}

            <div style={{ flex: 1, overflowY: "auto", padding: "4px 0", marginBottom: 12 }}>
                {history.length === 0 && (
                    <div style={{ padding: "24px 0", textAlign: "center", color: "#BDBDBD", fontSize: 12 }}>
                        {mode === "agent"
                            ? "Ask any question and all sampled agents will respond in character based on their simulation trace."
                            : "Ask follow-up questions about the simulation results, evidence, or methodology."}
                    </div>
                )}
                {history.map((m, i) => (
                    <Message key={i} role={m.role} content={m.content} />
                ))}
                {loading && (
                    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 12 }}>
                        <div style={{ padding: "10px 14px", background: "#F5F3EF", borderRadius: 2 }}>
                            <div style={{ display: "flex", gap: 4 }}>
                                {[0, 1, 2].map(i => (
                                    <div key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: "#9B9B9B", animation: `pulse 1s ${i * 0.2}s infinite` }} />
                                ))}
                            </div>
                        </div>
                    </div>
                )}
                <div ref={endRef} />
            </div>

            <form onSubmit={handleSend} style={{ display: "flex", gap: 8 }}>
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    disabled={loading}
                    placeholder={placeholder}
                    style={{ flex: 1, padding: "11px 14px", fontSize: 13, border: "1px solid #E8E4DF", borderRadius: 2, background: "#FFFFFF", color: "#1A1A1A", outline: "none", fontFamily: "inherit" }}
                />
                <button type="submit" disabled={loading || !input.trim()} style={{
                    padding: "11px 20px", fontSize: 10, fontWeight: 700,
                    letterSpacing: "0.15em", textTransform: "uppercase",
                    background: loading || !input.trim() ? "#E8E4DF" : "#1A1A1A",
                    color: loading || !input.trim() ? "#9B9B9B" : "#FFFFFF",
                    border: "none", borderRadius: 2, cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                }}>
                    Send
                </button>
            </form>
        </div>
    );
}