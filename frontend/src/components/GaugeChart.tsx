import { memo, useRef, useEffect } from "react";
import * as d3 from "d3";
import { useMetricsStore } from "../store/metricsSlice";

const WIDTH = 200;
const HEIGHT = 120;
const RADIUS = 80;
const MIN = 0;
const MAX = 20;

const ARC_BG = "#334155";
const COLORS: [number, string][] = [
  [0, "#10b981"],
  [5, "#f59e0b"],
  [10, "#ef4444"],
];

function getColor(value: number): string {
  for (let i = COLORS.length - 1; i >= 0; i--) {
    if (value >= COLORS[i][0]) return COLORS[i][1];
  }
  return COLORS[0][1];
}

function GaugeChartInner() {
  const svgRef = useRef<SVGSVGElement>(null);
  const errorRate = useMetricsStore((s) => s.live?.error_rate ?? 0);
  const prevRate = useRef(0);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg
      .append("g")
      .attr("transform", `translate(${WIDTH / 2}, ${HEIGHT})`);

    const arcGen = d3.arc<any>().innerRadius(RADIUS - 16).outerRadius(RADIUS);

    // Background arc
    g.append("path")
      .datum({ startAngle: -Math.PI / 2, endAngle: Math.PI / 2 })
      .attr("d", arcGen)
      .attr("fill", ARC_BG);

    // Value arc
    const clampedValue = Math.min(Math.max(errorRate, MIN), MAX);
    const endAngle = -Math.PI / 2 + (clampedValue / MAX) * Math.PI;
    const color = getColor(clampedValue);

    const valuePath = g
      .append("path")
      .datum({ startAngle: -Math.PI / 2, endAngle: -Math.PI / 2 })
      .attr("d", arcGen)
      .attr("fill", color);

    valuePath
      .transition()
      .duration(600)
      .ease(d3.easeCubicOut)
      .attrTween("d", function () {
        const interp = d3.interpolate(
          -Math.PI / 2 + (prevRate.current / MAX) * Math.PI,
          endAngle
        );
        return (t: number) =>
          arcGen({ startAngle: -Math.PI / 2, endAngle: interp(t) })!;
      });

    // Needle
    const needleLen = RADIUS - 24;
    const needleAngle = -Math.PI / 2 + (prevRate.current / MAX) * Math.PI;
    const needle = g
      .append("line")
      .attr("x1", 0).attr("y1", 0)
      .attr("x2", Math.cos(needleAngle) * needleLen)
      .attr("y2", Math.sin(needleAngle) * needleLen)
      .attr("stroke", "#e2e8f0")
      .attr("stroke-width", 2.5)
      .attr("stroke-linecap", "round");

    needle
      .transition()
      .duration(600)
      .ease(d3.easeCubicOut)
      .attr("x2", Math.cos(endAngle) * needleLen)
      .attr("y2", Math.sin(endAngle) * needleLen);

    // Center dot
    g.append("circle").attr("r", 5).attr("fill", "#e2e8f0");

    // Value text
    g.append("text")
      .attr("y", -20)
      .attr("text-anchor", "middle")
      .attr("fill", color)
      .attr("font-size", "22px")
      .attr("font-weight", "bold")
      .text(`${clampedValue.toFixed(1)}%`);

    prevRate.current = clampedValue;
  }, [errorRate]);

  return (
    <div className="bg-card-light dark:bg-card-dark rounded-xl border border-slate-200 dark:border-slate-700 p-6 flex flex-col items-center">
      <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
        Error Rate
      </h3>
      <svg ref={svgRef} width={WIDTH} height={HEIGHT} />
      <div className="flex justify-between w-full px-4 mt-1">
        <span className="text-xs text-slate-500">0%</span>
        <span className="text-xs text-slate-500">20%</span>
      </div>
    </div>
  );
}

export default memo(GaugeChartInner);
