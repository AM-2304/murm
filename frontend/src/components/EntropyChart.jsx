import { useEffect, useRef } from "react";
import * as d3 from "d3";

const M = { top: 12, right: 16, bottom: 28, left: 40 };

export function EntropyChart({ data, height = 160 }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current || !data || data.length === 0) return;
    const el = svgRef.current;
    const W = el.clientWidth || 560;
    const iW = W - M.left - M.right;
    const iH = height - M.top - M.bottom;

    d3.select(el).selectAll("*").remove();

    const svg = d3.select(el).attr("width", W).attr("height", height)
      .append("g").attr("transform", `translate(${M.left},${M.top})`);

    const xScale = d3.scaleLinear().domain([1, Math.max(data.length, 2)]).range([0, iW]);
    const yScale = d3.scaleLinear().domain([0, Math.log2(5) * 1.08]).range([iH, 0]);

    // Grid lines
    const gridLines = [0.5, 1.0, 1.5, 2.0, Math.log2(5)];
    gridLines.forEach(v => {
      svg.append("line")
        .attr("x1", 0).attr("x2", iW)
        .attr("y1", yScale(v)).attr("y2", yScale(v))
        .attr("stroke", "#E8E4DF").attr("stroke-width", v === Math.log2(5) ? 1 : 0.5)
        .attr("stroke-dasharray", v === Math.log2(5) ? "4 4" : "none");
      if (v === Math.log2(5)) {
        svg.append("text").attr("x", iW + 4).attr("y", yScale(v) + 4)
          .text("max").attr("font-size", 8).attr("fill", "#BDBDBD");
      }
    });

    // Area fill under curve
    const area = d3.area()
      .x((_, i) => xScale(i + 1))
      .y0(iH)
      .y1(d => yScale(d.opinion_entropy ?? d))
      .curve(d3.curveMonotoneX);

    svg.append("path").datum(data)
      .attr("fill", "#1A1A1A")
      .attr("fill-opacity", 0.06)
      .attr("d", area);

    // Line
    const line = d3.line()
      .x((_, i) => xScale(i + 1))
      .y(d => yScale(d.opinion_entropy ?? d))
      .curve(d3.curveMonotoneX);

    svg.append("path").datum(data)
      .attr("fill", "none")
      .attr("stroke", "#1A1A1A")
      .attr("stroke-width", 1.5)
      .attr("d", line);

    // Dots
    if (data.length <= 60) {
      svg.selectAll("circle").data(data).join("circle")
        .attr("cx", (_, i) => xScale(i + 1))
        .attr("cy", d => yScale(d.opinion_entropy ?? d))
        .attr("r", data.length > 30 ? 2 : 3)
        .attr("fill", "#FFFFFF")
        .attr("stroke", "#1A1A1A")
        .attr("stroke-width", 1.5);
    }

    // Axes
    svg.append("g").attr("transform", `translate(0,${iH})`).call(
      d3.axisBottom(xScale).ticks(Math.min(data.length, 8)).tickFormat(d3.format("d"))
    ).call(g => {
      g.select(".domain").attr("stroke", "#E8E4DF");
      g.selectAll("text").attr("font-size", 9).attr("fill", "#9B9B9B").attr("font-family", "Helvetica Neue, Helvetica, Arial, sans-serif");
      g.selectAll(".tick line").attr("stroke", "#E8E4DF");
    });

    svg.append("g").call(
      d3.axisLeft(yScale).ticks(4).tickFormat(d => d.toFixed(1))
    ).call(g => {
      g.select(".domain").remove();
      g.selectAll("text").attr("font-size", 9).attr("fill", "#9B9B9B").attr("font-family", "Helvetica Neue, Helvetica, Arial, sans-serif");
      g.selectAll(".tick line").attr("stroke", "#E8E4DF").attr("stroke-width", 0.5);
    });

    // Axis label
    svg.append("text").attr("x", -M.left + 2).attr("y", -2)
      .attr("font-size", 8).attr("fill", "#9B9B9B").text("bits");

  }, [data, height]);

  return <svg ref={svgRef} style={{ width: "100%", display: "block" }} height={height} />;
}