"use client";

// Xarajat taqsimoti donut diagrammasi (kategoriya bo'yicha).

import type { MouseEvent, ReactNode } from "react";

import { money } from "@/lib/format";
import { ChartTooltip, useChartTooltip } from "./ChartTooltip";

export interface DonutRow {
  label: string;
  total: number;
}

const PALETTE = [
  "var(--c1)",
  "var(--c2)",
  "var(--c3)",
  "var(--c4)",
  "var(--c5)",
  "var(--c6)",
  "var(--c7)",
];

export function Donut({
  rows,
  totalLabel,
}: {
  rows: DonutRow[];
  totalLabel: string;
}): ReactNode {
  const { tip, show, hide } = useChartTooltip();
  const total = rows.reduce((sum, r) => sum + r.total, 0);
  const sorted = [...rows].sort((a, b) => b.total - a.total);

  if (total <= 0) {
    return null;
  }

  const R = 68;
  const r = 44;
  const cx = 80;
  const cy = 80;
  let angle = -Math.PI / 2;
  const paths: ReactNode[] = [];

  sorted.forEach((row, i) => {
    const share = row.total / total;
    const nextAngle = angle + share * Math.PI * 2;
    const big = nextAngle - angle > Math.PI ? 1 : 0;
    const point = (radius: number, a: number): [number, number] => [
      cx + radius * Math.cos(a),
      cy + radius * Math.sin(a),
    ];
    const [x1, y1] = point(R, angle);
    const [x2, y2] = point(R, nextAngle);
    const [x3, y3] = point(r, nextAngle);
    const [x4, y4] = point(r, angle);
    const color = PALETTE[i % PALETTE.length];
    paths.push(
      <path
        key={row.label}
        d={`M${x1} ${y1} A${R} ${R} 0 ${big} 1 ${x2} ${y2} L${x3} ${y3} A${r} ${r} 0 ${big} 0 ${x4} ${y4}Z`}
        fill={color}
        stroke="var(--surface)"
        strokeWidth={2.5}
        style={{ cursor: "pointer" }}
        onMouseMove={(e: MouseEvent) =>
          show(
            e,
            <>
              {row.label}: <b>{money(row.total)}</b>
              <br />
              {((row.total / total) * 100).toFixed(1)}%
            </>,
          )
        }
        onMouseLeave={hide}
      />,
    );
    angle = nextAngle;
  });

  return (
    <div className="donut-wrap">
      <svg
        width={160}
        height={160}
        viewBox="0 0 160 160"
        style={{ flex: "none" }}
      >
        {paths}
        <text
          x="80"
          y="76"
          textAnchor="middle"
          fontSize="10"
          fill="var(--ink-3)"
        >
          {totalLabel.toUpperCase()}
        </text>
        <text
          x="80"
          y="94"
          textAnchor="middle"
          fontSize="15"
          fontWeight={700}
          fill="var(--ink)"
          fontFamily="var(--mono)"
        >
          {(total / 1e6).toFixed(1)}M
        </text>
      </svg>
      <div className="donut-legend">
        {sorted.map((row, i) => (
          <div key={row.label}>
            <i style={{ background: PALETTE[i % PALETTE.length] }} />
            <span style={{ flex: 1 }}>{row.label}</span>
            <span
              style={{
                color: "var(--ink-3)",
                fontSize: 11.5,
                fontFamily: "var(--mono)",
              }}
            >
              {((row.total / total) * 100).toFixed(0)}%
            </span>
            <b>{(row.total / 1e6).toFixed(1)}M</b>
          </div>
        ))}
      </div>
      <ChartTooltip tip={tip} />
    </div>
  );
}
