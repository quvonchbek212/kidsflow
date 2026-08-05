"use client";

// Oylik daromad/xarajat ustunli diagrammasi + ixtiyoriy zararsizlik chizig'i.
// Qiymatlar xom valyutada (so'm) keladi, ko'rsatishda mln'ga o'tkaziladi.

import type { MouseEvent, ReactNode } from "react";

import { money } from "@/lib/format";
import { ChartTooltip, useChartTooltip } from "./ChartTooltip";

export interface BarChartMonth {
  label: string;
  income: number;
  outcome: number;
}

export function BarChart({
  data,
  breakeven,
  incomeLabel,
  outcomeLabel,
  breakevenLabel,
}: {
  data: BarChartMonth[];
  breakeven?: number | null;
  incomeLabel: string;
  outcomeLabel: string;
  breakevenLabel: string;
}): ReactNode {
  const { tip, show, hide } = useChartTooltip();
  const W = 680;
  const H = 280;
  const padL = 46;
  const padB = 32;
  const padT = 16;
  const mlnf = (v: number) => v / 1e6;

  const maxVal = Math.max(
    1,
    ...data.map((m) => Math.max(mlnf(m.income), mlnf(m.outcome))),
    breakeven ? mlnf(breakeven) : 0,
  );
  const max = Math.ceil((maxVal * 1.15) / 10) * 10 || maxVal * 1.15 || 10;

  const cw = data.length > 0 ? (W - padL) / data.length : W - padL;
  const y = (v: number) => padT + (H - padT - padB) * (1 - v / max);

  const gridLines = [];
  for (let v = 0; v <= max; v += Math.max(1, Math.round(max / 4))) {
    gridLines.push(v);
  }

  return (
    <div style={{ position: "relative" }}>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`}>
        {gridLines.map((v) => (
          <g key={v}>
            <line className="axis" x1={padL} y1={y(v)} x2={W} y2={y(v)} />
            <text x={padL - 10} y={y(v) + 4} textAnchor="end">
              {v}
            </text>
          </g>
        ))}
        {data.map((m, i) => {
          const x = padL + i * cw;
          const bw = (cw - 22) / 2;
          const incomeM = mlnf(m.income);
          const outcomeM = mlnf(m.outcome);
          return (
            <g key={m.label}>
              <rect
                x={x + 4}
                y={padT}
                width={cw - 8}
                height={H - padB - padT}
                fill="transparent"
                onMouseMove={(e: MouseEvent) =>
                  show(
                    e,
                    <>
                      {m.label}
                      <br />
                      {incomeLabel}: <b>{money(m.income)}</b>
                      <br />
                      {outcomeLabel}: <b>{money(m.outcome)}</b>
                    </>,
                  )
                }
                onMouseLeave={hide}
              />
              <rect
                x={x + 8}
                y={y(incomeM)}
                width={bw}
                height={H - padB - y(incomeM)}
                rx={3.5}
                fill="var(--bar-1)"
              />
              <rect
                className="bar-out"
                x={x + 10 + bw}
                y={y(outcomeM)}
                width={bw}
                height={H - padB - y(outcomeM)}
                rx={3.5}
                fill="var(--bar-2)"
              />
              <text x={x + cw / 2} y={H - 9} textAnchor="middle">
                {m.label}
              </text>
            </g>
          );
        })}
        {breakeven != null &&
          (() => {
            // Yorliq mockupdagidek to'la bo'yalgan kapsula ichida va CHAP
            // tomonda — shunda o'ng tarafdagi baland ustunlarni to'smaydi va
            // matn ustunlar ustiga tushib o'qilmay qolmaydi.
            const label = `${breakevenLabel} · ${mlnf(breakeven).toFixed(1)}M`;
            const lw = label.length * 6.1 + 18;
            const ly = y(mlnf(breakeven));
            return (
              <g>
                <line
                  className="be-line"
                  x1={padL}
                  y1={ly}
                  x2={W}
                  y2={ly}
                  strokeWidth={1.75}
                  strokeDasharray="7 6"
                  strokeLinecap="round"
                />
                <rect x={padL + 6} y={ly - 30} width={lw} height={22} rx={6} fill="var(--be-fill)" />
                <path d={`M${padL + 16} ${ly - 8} l5 5 l5 -5 Z`} fill="var(--be-fill)" />
                <text
                  className="on-solid"
                  x={padL + 6 + lw / 2}
                  y={ly - 15}
                  textAnchor="middle"
                  fontSize="11.5"
                >
                  {label}
                </text>
              </g>
            );
          })()}
      </svg>
      <ChartTooltip tip={tip} />
    </div>
  );
}
