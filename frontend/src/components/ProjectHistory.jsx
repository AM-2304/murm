import { useState, useEffect } from "react";
import { api } from "../api/client";

const STATUS_STYLE = {
    created: { color: "#9B9B9B", label: "CREATED" },
    building_graph: { color: "#D4600A", label: "BUILDING" },
    ready: { color: "#1A7F4B", label: "READY" },
    error: { color: "#C0392B", label: "ERROR" },
};

export function ProjectHistory({ onSelect, currentProjectId }) {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.listProjects()
            .then(setProjects)
            .catch(() => setProjects([]))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div style={{ padding: 24, textAlign: "center" }}>
            <div style={{ width: 18, height: 18, border: "2px solid #E8E4DF", borderTopColor: "#1A1A1A", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto" }} />
        </div>
    );

    if (projects.length === 0) return (
        <div style={{ padding: 24, textAlign: "center", fontSize: 12, color: "#BDBDBD" }}>
            No previous projects
        </div>
    );

    return (
        <div>
            {projects.map(p => {
                const s = STATUS_STYLE[p.status] || STATUS_STYLE.created;
                const isCurrent = p.project_id === currentProjectId;
                return (
                    <div
                        key={p.project_id}
                        onClick={() => p.status === "ready" && onSelect(p)}
                        style={{
                            padding: "12px 16px",
                            borderBottom: "1px solid #E8E4DF",
                            cursor: p.status === "ready" ? "pointer" : "default",
                            background: isCurrent ? "#F0F4FF" : "transparent",
                            transition: "background 0.15s",
                        }}
                        onMouseEnter={e => { if (!isCurrent && p.status === "ready") e.currentTarget.style.background = "#FAFAF8"; }}
                        onMouseLeave={e => { if (!isCurrent) e.currentTarget.style.background = "transparent"; }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ fontSize: 13, fontWeight: isCurrent ? 600 : 400, color: "#1A1A1A", marginBottom: 3 }}>
                                {p.title}
                            </div>
                            <span style={{ fontSize: 8, fontWeight: 700, letterSpacing: "0.1em", color: s.color, marginLeft: 8 }}>
                                {s.label}
                            </span>
                        </div>
                        <div style={{ fontSize: 10, color: "#9B9B9B" }}>
                            {new Date(p.created_at * 1000).toLocaleString()}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}