"use client";

// Grafiklar uchun umumiy sichqoncha-tooltip (har bir chart o'z holatini boshqaradi).

import { useState, type MouseEvent, type ReactNode } from "react";

export function useChartTooltip(): {
  tip: { x: number; y: number; content: ReactNode } | null;
  show: (e: MouseEvent, content: ReactNode) => void;
  hide: () => void;
} {
  const [tip, setTip] = useState<{
    x: number;
    y: number;
    content: ReactNode;
  } | null>(null);

  function show(e: MouseEvent, content: ReactNode): void {
    setTip({ x: e.clientX + 14, y: e.clientY - 12, content });
  }
  function hide(): void {
    setTip(null);
  }

  return { tip, show, hide };
}

export function ChartTooltip({
  tip,
}: {
  tip: { x: number; y: number; content: ReactNode } | null;
}): ReactNode {
  if (!tip) return null;
  return (
    <div className="chart-tip on" style={{ left: tip.x, top: tip.y }}>
      {tip.content}
    </div>
  );
}
