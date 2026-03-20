const ROLE_COLORS = {
    influencer: "#0057B8",
    active_user: "#1A7F4B",
    passive_user: "#9B9B9B",
    skeptic: "#C0392B",
    amplifier: "#D4600A",
};
const OPINION_COLORS = {
    strongly_agree: "#1A7F4B",
    agree: "#6DB88F",
    neutral: "#9B9B9B",
    disagree: "#D4896A",
    strongly_disagree: "#C0392B",
};
const OPINION_WIDTHS = {
    strongly_agree: 100, agree: 75, neutral: 50, disagree: 25, strongly_disagree: 0,
};

function AgentCard({ agent }) {
    const roleColor = ROLE_COLORS[agent.influence_role] || "#9B9B9B";
    const opinionColor = OPINION_COLORS[agent.opinion_bias] || "#9B9B9B";
    const opinionPct = OPINION_WIDTHS[agent.opinion_bias] ?? 50;

    return (
        <div style={{
            background: "#FAFAF8", border: "1px solid #E8E4DF", borderRadius: 2,
            padding: "12px 14px",
        }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1A1A1A", lineHeight: 1.2 }}>
                    {agent.name}
                </div>
                <span style={{
                    fontSize: 8, fontWeight: 700, letterSpacing: "0.1em",
                    color: roleColor, background: `${roleColor}15`,
                    border: `1px solid ${roleColor}30`,
                    padding: "2px 6px", borderRadius: 2, whiteSpace: "nowrap",
                    textTransform: "uppercase",
                }}>
                    {agent.influence_role?.replace(/_/g, " ")}
                </span>
            </div>
            <div style={{ fontSize: 10, color: "#6B6B6B", marginBottom: 8 }}>
                {agent.age}y · {agent.occupation}
            </div>
            {agent.expertise_domains?.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 8 }}>
                    {agent.expertise_domains.slice(0, 3).map((d, i) => (
                        <span key={i} style={{
                            fontSize: 9, padding: "1px 6px",
                            background: "#F0EBE3", color: "#6B6B6B",
                            borderRadius: 2, border: "1px solid #E8E4DF",
                        }}>{d}</span>
                    ))}
                </div>
            )}
            <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ fontSize: 9, color: "#9B9B9B", letterSpacing: "0.05em" }}>Initial stance</span>
                    <span style={{ fontSize: 9, color: opinionColor, fontWeight: 600 }}>
                        {agent.opinion_bias?.replace(/_/g, " ")}
                    </span>
                </div>
                <div style={{ height: 3, background: "#E8E4DF", borderRadius: 2 }}>
                    <div style={{ height: "100%", width: `${opinionPct}%`, background: opinionColor, borderRadius: 2, transition: "width 0.4s" }} />
                </div>
            </div>
        </div>
    );
}

export function AgentRoster({ agents }) {
    if (!agents || agents.length === 0) return (
        <div style={{ padding: 32, textAlign: "center", color: "#BDBDBD", fontSize: 12 }}>
            Agents will appear here after population generation
        </div>
    );

    const roleGroups = agents.reduce((acc, a) => {
        const r = a.influence_role || "unknown";
        if (!acc[r]) acc[r] = [];
        acc[r].push(a);
        return acc;
    }, {});

    return (
        <div>
            <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
                {Object.entries(roleGroups).map(([role, group]) => (
                    <div key={role} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                        <div style={{ width: 8, height: 8, borderRadius: "50%", background: ROLE_COLORS[role] || "#9B9B9B" }} />
                        <span style={{ fontSize: 10, color: "#6B6B6B" }}>
                            {role.replace(/_/g, " ")} ({group.length})
                        </span>
                    </div>
                ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8, maxHeight: 400, overflowY: "auto" }}>
                {agents.map((a, i) => <AgentCard key={i} agent={a} />)}
            </div>
        </div>
    );
}