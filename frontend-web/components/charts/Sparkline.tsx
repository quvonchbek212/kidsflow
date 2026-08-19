"use client";

// Davomat trendi uchun oddiy chiziqli sparkline (`GET /attendance/trend`dan).

import type { MouseEvent, ReactNode } from "react";

import { ChartTooltip, useChartTooltip } from "./ChartTooltip";

export interface SparklinePoint {
  label: string;
  present: number;
  total: number;
}

export function Sparkline({ points }: { points: SparklinePoint[] }): ReactNode {
  const { tip, show, hide } = useChartTooltip();
  if (points.length === 0) return null;

  const W = 560;
  const H = 150;
  const padL = 30;
  const padB = 24;
  const padT = 12;
  const maxTotal = Math.max(1, ...points.map((p) => p.total));

  const x = (i: number) =>
    padL + i * ((W - padL) / Math.max(1, points.length - 1));
  const y = (v: number) => padT + (H - padT - padB) * (1 - v / maxTotal);

  const pts = points.map((p, i) => `${x(i)},${y(p.present)}`).join(" ");

  return (
    <div style={{ position: "relative" }}>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`}>
        <polygon
          points={`${padL},${H - padB} ${pts} ${x(points.length - 1)},${H - padB}`}
          fill="var(--brand-bg)"
        />
        <polyline
          points={pts}
          fill="none"
          stroke="var(--brand-2)"
          strokeWidth={2.2}
        />
        {points.map((p, i) => (
          <circle
            key={p.label}
            cx={x(i)}
            cy={y(p.present)}
            r={5}
            fill="var(--surface)"
            stroke="var(--brand-2)"
            strokeWidth={2}
            style={{ cursor: "pointer" }}
            onMouseMove={(e: MouseEvent) =>
              show(
                e,
                <>
                  {p.label} —{" "}
                  <b>
                    {p.present}/{p.total}
                  </b>{" "}
                  ({p.total > 0 ? Math.round((p.present / p.total) * 100) : 0}%)
                </>,
              )
            }
            onMouseLeave={hide}
          />
        ))}
        {points.map((p, i) => (
          <text key={p.label} x={x(i)} y={H - 7} textAnchor="middle">
            {p.label}
          </text>
        ))}
      </svg>
      <ChartTooltip tip={tip} />
    </div>
  );
}
