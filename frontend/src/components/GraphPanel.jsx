import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";

// Entity type color palette — matches MURM's cream/dark aesthetic with vivid categorical distinction
const TYPE_PALETTE = {
  person: { fill: "#C0392B", stroke: "#922B21" },
  company: { fill: "#0057B8", stroke: "#003F8A" },
  organization: { fill: "#6B21A8", stroke: "#4A1575" },
  government: { fill: "#1A7F4B", stroke: "#145C36" },
  governmentagency: { fill: "#1A7F4B", stroke: "#145C36" },
  policymaker: { fill: "#1A7F4B", stroke: "#145C36" },
  media: { fill: "#D4600A", stroke: "#A04508" },
  mediaoutlet: { fill: "#D4600A", stroke: "#A04508" },
  investor: { fill: "#0097A7", stroke: "#006978" },
  investorinstitution: { fill: "#0097A7", stroke: "#006978" },
  event: { fill: "#E91E8C", stroke: "#B01568" },
  concept: { fill: "#7B7B7B", stroke: "#555555" },
  location: { fill: "#558B2F", stroke: "#38601F" },
  policy: { fill: "#F57F17", stroke: "#B85A10" },
  technology: { fill: "#1565C0", stroke: "#0D3F7A" },
  product: { fill: "#6A1B9A", stroke: "#4A1270" },
  entity: { fill: "#546E7A", stroke: "#37474F" },
  default: { fill: "#8D6E63", stroke: "#5D4037" },
};

function getTypeColor(type) {
  if (!type) return TYPE_PALETTE.default;
  const key = type.toLowerCase().replace(/[^a-z]/g, "");
  return TYPE_PALETTE[key] || TYPE_PALETTE.default;
}

function getTypeLabel(type) {
  if (!type) return "Entity";
  return type.charAt(0).toUpperCase() + type.slice(1).toLowerCase().replace(/_/g, " ");
}

// Derive a stable unique list of entity types present in the graph
function getEntityTypes(nodes) {
  const seen = new Set();
  const types = [];
  for (const n of nodes) {
    const t = (n.entity_type || n.type || "entity").toLowerCase().replace(/[^a-z]/g, "");
    if (!seen.has(t)) { seen.add(t); types.push({ key: t, label: getTypeLabel(n.entity_type || n.type || "entity"), color: getTypeColor(n.entity_type || n.type) }); }
  }
  return types;
}

export function GraphPanel({ graphData, height = 460, liveActions = [] }) {
  const svgRef = useRef(null);
  const simRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const [hoveredType, setHoveredType] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [activeNodeIds, setActiveNodeIds] = useState(new Set());
  const [dynamicGraph, setDynamicGraph] = useState(null);

  // 1. Sync initial backend graph
  useEffect(() => {
    if (!graphData) return;
    setDynamicGraph(prev => {
      if (!prev || prev.nodes.length !== graphData.nodes?.length) {
         return JSON.parse(JSON.stringify(graphData)); 
      }
      return prev;
    });
  }, [graphData]);

  // 2. Real-time extraction: Physically grow the graph as agents talk!
  useEffect(() => {
    if (!liveActions?.length || !dynamicGraph) return;
    const lastAction = liveActions[liveActions.length - 1];
    if (!lastAction.content || lastAction.action_type === 'external_event') return;

    const words = lastAction.content.split(/[^\w]+/);
    const newEntities = words.filter(w => w.length > 4 && w[0] === w[0].toUpperCase() && w.toUpperCase() !== w);
    
    if (newEntities.length === 0) return;

    setDynamicGraph(prev => {
      const next = { nodes: [...prev.nodes], edges: [...(prev.edges || prev.links || [])] };
      const agentId = `agent_${lastAction.agent_id}`;
      
      let added = false;
      if (!next.nodes.find(n => n.id === agentId)) {
         // Drop in the agent node
         next.nodes.push({ id: agentId, name: lastAction.agent_id.split('-')[0], type: "Person" });
         added = true;
      }

      for (const ent of new Set(newEntities.slice(0, 3))) {
        const entId = `dyn_${ent.toLowerCase()}`;
        if (!next.nodes.find(n => n.id === entId)) {
          next.nodes.push({ id: entId, name: ent, type: "Concept" });
          added = true;
        }
        // Link agent to their mentioned concept
        if (!next.edges.find(e => (e.source.id || e.source) === agentId && (e.target.id || e.target) === entId)) {
          next.edges.push({ source: agentId, target: entId, relation: "DISCUSSES" });
          added = true;
        }
      }
      return added ? next : prev;
    });
  }, [liveActions]);

  // Pulse nodes that match recently-active agent names from live actions
  useEffect(() => {
    if (!liveActions?.length || !dynamicGraph?.nodes) return;
    const recentNames = new Set(
      liveActions.slice(-5)
        .map(a => a.agent_id?.split("-")[0]?.toLowerCase())
        .filter(Boolean)
    );
    const matchedIds = new Set(
      (dynamicGraph.nodes || []).filter(n =>
        recentNames.has((n.name || "").toLowerCase().split(" ")[0])
      ).map(n => n.id)
    );
    if (matchedIds.size) {
      setActiveNodeIds(matchedIds);
      const timer = setTimeout(() => setActiveNodeIds(new Set()), 2500);
      return () => clearTimeout(timer);
    }
  }, [liveActions, dynamicGraph]);

  const draw = useCallback(() => {
    if (!svgRef.current || !dynamicGraph) return;
    
    // Create a copy of the graph to run the physics simulation on
    const nodes = (dynamicGraph.nodes || []).map(n => ({ ...n }));
    const rawEdges = dynamicGraph.edges || dynamicGraph.links || [];
    const nodeIndex = {};
    nodes.forEach(n => { nodeIndex[n.id] = n; });
    const edges = rawEdges
      .filter(e => {
        const s = typeof e.source === "object" ? e.source.id : e.source;
        const t = typeof e.target === "object" ? e.target.id : e.target;
        return nodeIndex[s] && nodeIndex[t];
      })
      .map(e => ({ ...e }));

    if (!nodes.length) return;

    const el = svgRef.current;
    const W = el.clientWidth || 700;
    const H = height;

    // Clear and redraw is acceptable here because React's fast DOM update
    // will just make the graph pop organically when an agent builds a new entity hook.
    d3.select(el).selectAll("*").remove();

    const svg = d3.select(el).attr("width", W).attr("height", H);

    // Background
    svg.append("rect").attr("width", W).attr("height", H).attr("fill", "#0D0D0D").attr("rx", 4);

    // Subtle grid
    const gridG = svg.append("g").attr("opacity", 0.08);
    for (let x = 0; x < W; x += 40) gridG.append("line").attr("x1", x).attr("x2", x).attr("y1", 0).attr("y2", H).attr("stroke", "#FFFFFF").attr("stroke-width", 0.5);
    for (let y = 0; y < H; y += 40) gridG.append("line").attr("x1", 0).attr("x2", W).attr("y1", y).attr("y2", y).attr("stroke", "#FFFFFF").attr("stroke-width", 0.5);

    const g = svg.append("g");

    const zoomBehavior = d3.zoom()
      .scaleExtent([0.2, 6])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
        setZoom(+event.transform.k.toFixed(2));
      });
    svg.call(zoomBehavior);
    svg.on("click", (event) => {
      if (event.target === el || event.target.tagName === "rect") setSelected(null);
    });

    // Edge lines
    const linkG = g.append("g");
    const link = linkG.selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "#FFFFFF")
      .attr("stroke-width", 0.5)
      .attr("stroke-opacity", 0.15);

    // Edge labels (relation type)
    const linkLabel = g.append("g").selectAll("text")
      .data(edges.filter(e => e.relation))
      .join("text")
      .text(d => d.relation)
      .attr("font-size", 8)
      .attr("fill", "#FFFFFF")
      .attr("fill-opacity", 0.3)
      .attr("text-anchor", "middle")
      .attr("pointer-events", "none");

    // Node groups
    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3.drag()
          .on("start", (event, d) => {
            if (!event.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on("end", (event, d) => {
            if (!event.active) sim.alphaTarget(0);
            d.fx = null; d.fy = null;
          })
      )
      .on("click", (event, d) => {
        event.stopPropagation();
        setSelected(d);
      });

    // Glow circle behind node
    node.append("circle")
      .attr("r", d => nodeRadius(d) + 4)
      .attr("fill", d => getTypeColor(d.entity_type || d.type).fill)
      .attr("fill-opacity", 0.15)
      .attr("stroke", "none");

    // Main node circle
    node.append("circle")
      .attr("r", nodeRadius)
      .attr("fill", d => getTypeColor(d.entity_type || d.type).fill)
      .attr("stroke", d => getTypeColor(d.entity_type || d.type).stroke)
      .attr("stroke-width", 1.5);

    // Active pulse ring — shown when a live agent action matches this node
    node.append("circle")
      .attr("class", "pulse-ring")
      .attr("r", d => nodeRadius(d) + 6)
      .attr("fill", "none")
      .attr("stroke", d => getTypeColor(d.entity_type || d.type).fill)
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0);

    // Node label
    node.append("text")
      .text(d => truncate(d.name || d.id, 14))
      .attr("text-anchor", "middle")
      .attr("dy", d => nodeRadius(d) + 12)
      .attr("font-size", 9)
      .attr("fill", "#FFFFFF")
      .attr("fill-opacity", 0.75)
      .attr("pointer-events", "none")
      .attr("font-family", "Helvetica Neue, Helvetica, Arial, sans-serif");

    // Simulation
    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id(d => d.id).distance(80).strength(0.4))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(W / 2, H / 2))
      .force("collision", d3.forceCollide(d => nodeRadius(d) + 8));
    simRef.current = sim;

    sim.on("tick", () => {
      link
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      linkLabel
        .attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2);
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Hover effect
    node
      .on("mouseenter", function (event, d) {
        d3.select(this).select("circle:nth-child(2)")
          .attr("r", nodeRadius(d) + 3)
          .attr("stroke-width", 2.5);
        link
          .attr("stroke-opacity", e => {
            const sid = typeof e.source === "object" ? e.source.id : e.source;
            const tid = typeof e.target === "object" ? e.target.id : e.target;
            return sid === d.id || tid === d.id ? 0.8 : 0.05;
          })
          .attr("stroke-width", e => {
            const sid = typeof e.source === "object" ? e.source.id : e.source;
            const tid = typeof e.target === "object" ? e.target.id : e.target;
            return sid === d.id || tid === d.id ? 1.5 : 0.5;
          });
      })
      .on("mouseleave", function (event, d) {
        d3.select(this).select("circle:nth-child(2)")
          .attr("r", nodeRadius(d))
          .attr("stroke-width", 1.5);
        link.attr("stroke-opacity", 0.15).attr("stroke-width", 0.5);
      });

    return () => sim.stop();
  }, [graphData, height]);

  // Apply pulse animation whenever activeNodeIds changes — runs independently of full redraw
  useEffect(() => {
    if (!svgRef.current) return;
    d3.select(svgRef.current).selectAll(".pulse-ring")
      .attr("stroke-opacity", d => activeNodeIds.has(d.id) ? 0.8 : 0)
      .attr("r", d => activeNodeIds.has(d.id) ? nodeRadius(d) + 9 : nodeRadius(d) + 6);
  }, [activeNodeIds]);

  useEffect(() => {
    const cleanup = draw();
    return cleanup;
  }, [draw]);

  useEffect(() => {
    const obs = new ResizeObserver(() => draw());
    if (svgRef.current) obs.observe(svgRef.current.parentElement);
    return () => obs.disconnect();
  }, [draw]);

  const entityTypes = dynamicGraph ? getEntityTypes(dynamicGraph.nodes || []) : [];

  return (
    <div style={{ position: "relative", background: "#0D0D0D", borderRadius: 4, overflow: "hidden" }}>
      <svg ref={svgRef} style={{ width: "100%", display: "block" }} height={height} />

      {/* Zoom indicator */}
      <div style={{ position: "absolute", top: 10, right: 10, fontSize: 9, color: "#FFFFFF", opacity: 0.4, letterSpacing: "0.1em", fontFamily: "monospace" }}>
        {(zoom * 100).toFixed(0)}%
      </div>

      {/* Controls hint */}
      <div style={{ position: "absolute", bottom: 10, left: 12, fontSize: 9, color: "#FFFFFF", opacity: 0.35, letterSpacing: "0.08em" }}>
        SCROLL TO ZOOM  ·  DRAG TO MOVE  ·  CLICK NODE FOR DETAILS
      </div>

      {/* Legend */}
      <div style={{
        position: "absolute", bottom: 10, right: 10,
        background: "rgba(0,0,0,0.7)", border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 3, padding: "8px 12px", maxWidth: 180,
      }}>
        <p style={{ fontSize: 8, color: "#FFFFFF", opacity: 0.5, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 7, fontWeight: 700 }}>Entity Types</p>
        {entityTypes.slice(0, 8).map(t => (
          <div key={t.key} style={{
            display: "flex", alignItems: "center", gap: 6, marginBottom: 4,
            opacity: hoveredType && hoveredType !== t.key ? 0.3 : 1, transition: "opacity 0.15s",
            cursor: "default"
          }}
            onMouseEnter={() => setHoveredType(t.key)}
            onMouseLeave={() => setHoveredType(null)}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: t.color.fill, flexShrink: 0 }} />
            <span style={{ fontSize: 9, color: "#FFFFFF", opacity: 0.8 }}>{t.label}</span>
          </div>
        ))}
        {entityTypes.length > 8 && <p style={{ fontSize: 8, color: "#FFFFFF", opacity: 0.3, marginTop: 4 }}>+{entityTypes.length - 8} more</p>}
      </div>

      {/* Node detail panel */}
      {selected && (
        <div style={{
          position: "absolute", top: 10, left: 10,
          background: "rgba(10,10,10,0.95)", border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 4, padding: "16px 18px", width: 240,
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: getTypeColor(selected.entity_type || selected.type).fill, flexShrink: 0 }} />
              <span style={{ fontSize: 9, color: "#FFFFFF", opacity: 0.5, letterSpacing: "0.12em", textTransform: "uppercase" }}>
                {getTypeLabel(selected.entity_type || selected.type)}
              </span>
            </div>
            <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "#FFFFFF", opacity: 0.4, cursor: "pointer", fontSize: 14, lineHeight: 1, padding: 0, marginTop: -2 }}>
              x
            </button>
          </div>

          <p style={{ fontSize: 14, fontWeight: 600, color: "#FFFFFF", marginBottom: 10, lineHeight: 1.3 }}>
            {selected.name || selected.id}
          </p>

          {selected.summary && (
            <p style={{ fontSize: 11, color: "#FFFFFF", opacity: 0.6, lineHeight: 1.6, marginBottom: 10, borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: 10 }}>
              {selected.summary}
            </p>
          )}

          <div style={{ borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: 10 }}>
            {selected.id && (
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 9, color: "#FFFFFF", opacity: 0.4, letterSpacing: "0.1em", textTransform: "uppercase" }}>ID</span>
                <span style={{ fontSize: 9, color: "#FFFFFF", opacity: 0.65, fontFamily: "monospace" }}>{String(selected.id).slice(0, 20)}</span>
              </div>
            )}
            {selected.entity_type && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 9, color: "#FFFFFF", opacity: 0.4, letterSpacing: "0.1em", textTransform: "uppercase" }}>Type</span>
                <span style={{ fontSize: 9, color: "#FFFFFF", opacity: 0.65 }}>{selected.entity_type}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function nodeRadius(d) {
  // Larger nodes for entities with more connections or higher importance
  const base = 6;
  if (d.connections) return base + Math.min(d.connections * 1.5, 12);
  return base;
}

function truncate(str, n) {
  if (!str) return "";
  return str.length > n ? str.slice(0, n) + "..." : str;
}