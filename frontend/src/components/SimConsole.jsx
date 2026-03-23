import { useRef, useEffect } from "react";

const TYPE_STYLES = {
    system_log: { color: "#9B9B9B", prefix: "SYS" },
    agents_ready: { color: "#1A7F4B", prefix: "AGT" },
    round_completed: { color: "#0057B8", prefix: "RND" },
    event_injected: { color: "#C0392B", prefix: "EVT" },
    simulation_ended: { color: "#1A7F4B", prefix: "END" },
    simulation_failed: { color: "#C0392B", prefix: "ERR" },
    simulation_started: { color: "#6B6B6B", prefix: "SIM" },
};

function formatLine(event) {
    const s = TYPE_STYLES[event.type] || { color: "#6B6B6B", prefix: "---" };
    const ts = new Date((event.timestamp || Date.now()) * 1000).toTimeString().slice(0, 8);
    let text = "";
    const p = event.payload || {};
    switch (event.type) {
        case "system_log":
            text = p.message || "";
            break;
        case "agents_ready":
            text = `${p.n_agents || (p.profiles ? p.profiles.length : "undefined")} agents generated`;
            break;
        case "round_completed":
            text = `Round ${p.round} — ${p.actions} actions — entropy ${p.metrics?.opinion_entropy?.toFixed(3) ?? "—"}`;
            break;
        case "event_injected":
            text = `Event injected: "${(p.content || "").slice(0, 80)}"`;
            break;
        case "simulation_ended":
            text = `Simulation complete — ${p.total_actions} total actions`;
            break;
        case "simulation_failed":
            text = `Failed: ${p.error || "unknown error"}`;
            break;
        case "simulation_started":
            text = `Simulation started — ${p.n_agents} agents`;
            break;
        default:
            text = event.type;
    }
    return { ts, prefix: s.prefix, color: s.color, text };
}

export function SimConsole({ events }) {
    const endRef = useRef(null);
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [events?.length]);

    const lines = (events || []).filter(e => e.type !== "round_completed" || true);

    return (
        <div style={{
            background: "#0D0D0D", borderRadius: 2, border: "1px solid #2A2A2A",
            height: 240, overflow: "hidden", display: "flex", flexDirection: "column",
        }}>
            <div style={{
                padding: "7px 12px", borderBottom: "1px solid #1E1E1E",
                display: "flex", alignItems: "center", gap: 8,
            }}>
                <div style={{ display: "flex", gap: 5 }}>
                    {["#C0392B", "#F39C12", "#27AE60"].map((c, i) => (
                        <div key={i} style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />
                    ))}
                </div>
                <span style={{ fontSize: 9, color: "#4A4A4A", letterSpacing: "0.15em", textTransform: "uppercase" }}>
                    System Console
                </span>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "8px 12px", fontFamily: "monospace" }}>
                {lines.length === 0 ? (
                    <div style={{ fontSize: 10, color: "#3A3A3A" }}>Waiting for simulation to start...</div>
                ) : (
                    lines.map((ev, i) => {
                        const { ts, prefix, color, text } = formatLine(ev);
                        return (
                            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 2, lineHeight: 1.4 }}>
                                <span style={{ fontSize: 9, color: "#3A3A3A", flexShrink: 0 }}>{ts}</span>
                                <span style={{ fontSize: 9, color, fontWeight: 700, flexShrink: 0, minWidth: 28 }}>{prefix}</span>
                                <span style={{ fontSize: 10, color: "#C8C8C8" }}>{text}</span>
                            </div>
                        );
                    })
                )}
                <div ref={endRef} />
            </div>
        </div>
    );
}