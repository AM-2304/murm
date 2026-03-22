import { useRef, useEffect } from "react";

const ACTION_COLORS = {
    post: { bg: "#F0F4FF", border: "#0057B8", label: "POST" },
    reply: { bg: "#F0FFF5", border: "#1A7F4B", label: "REPLY" },
    share: { bg: "#FFF8F0", border: "#D4600A", label: "SHARE" },
    external_event: { bg: "#FFF0F0", border: "#C0392B", label: "EVENT" },
    default: { bg: "#FAFAF8", border: "#9B9B9B", label: "ACT" },
};

function ActionRow({ action, idx }) {
    const c = ACTION_COLORS[action.action_type] || ACTION_COLORS.default;
    return (
        <div style={{
            padding: "10px 14px",
            borderBottom: "1px solid #F0EBE3",
            display: "flex", gap: 12, alignItems: "flex-start",
            background: idx % 2 === 0 ? "#FFFFFF" : "#FAFAF8",
            animation: "fadeRow 0.3s ease",
        }}>
            <div style={{ flexShrink: 0, textAlign: "right", minWidth: 48 }}>
                <div style={{ fontSize: 9, color: "#9B9B9B", letterSpacing: "0.08em", marginBottom: 2 }}>
                    R{action.round}
                </div>
                <div style={{
                    display: "inline-block", padding: "2px 6px",
                    background: c.bg, border: `1px solid ${c.border}`,
                    borderRadius: 2, fontSize: 8, fontWeight: 700,
                    color: c.border, letterSpacing: "0.1em",
                }}>
                    {c.label}
                </div>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 10, color: "#9B9B9B", marginBottom: 3, letterSpacing: "0.05em" }}>
                    {action.agent_id?.slice(0, 8) || "agent"}
                </div>
                <div style={{ fontSize: 12, color: "#2A2A2A", lineHeight: 1.55, wordBreak: "break-word" }}>
                    {action.content || <span style={{ color: "#BDBDBD", fontStyle: "italic" }}>no content</span>}
                </div>
                {action.opinion_shift && (
                    <div style={{ marginTop: 4, fontSize: 9, color: "#6B6B6B", letterSpacing: "0.05em" }}>
                        stance: {action.opinion_shift.replace(/_/g, " ")}
                    </div>
                )}
            </div>
        </div>
    );
}

export function AgentFeed({ actions, status }) {
    const endRef = useRef(null);
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [actions?.length]);

    return (
        <div style={{ background: "#FFFFFF", border: "1px solid #E8E4DF", borderRadius: 2 }}>
            <div style={{
                padding: "12px 16px", borderBottom: "1px solid #E8E4DF",
                display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
                <p style={{ fontSize: 10, letterSpacing: "0.15em", textTransform: "uppercase", color: "#9B9B9B", fontWeight: 600 }}>
                    Live Action Feed
                </p>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {status === "running" && (
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#1A7F4B", animation: "pulse 1s infinite", display: "inline-block" }} />
                    )}
                    <span style={{ fontSize: 10, color: "#9B9B9B" }}>{actions?.length || 0} actions</span>
                </div>
            </div>
            <div style={{ height: 340, overflowY: "auto" }}>
                {(!actions || actions.length === 0) ? (
                    <div style={{ padding: 32, textAlign: "center", color: "#BDBDBD", fontSize: 12 }}>
                        {status === "running" ? "Waiting for first agent action..." : "No actions yet"}
                    </div>
                ) : (
                    actions.map((a, i) => <ActionRow key={i} action={a} idx={i} />)
                )}
                <div ref={endRef} />
            </div>
        </div>
    );
}