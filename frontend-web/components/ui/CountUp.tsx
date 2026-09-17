"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

const DURATION = 900;

/**
 * Raqamni oldingi qiymatdan yangisiga sanab chiqadi.
 *
 * Birinchi yuklashda oldingi qiymat 0 bo'ladi — ya'ni son 0 dan o'sadi.
 * Keyinchalik davr yoki filial almashsa, 0 ga qaytmasdan hozirgi sondan
 * yangisiga o'tadi: har o'zgarishda noldan boshlash chalg'itardi.
 */
export function useCountUp(target: number, duration = DURATION): number {
  const [value, setValue] = useState(0);
  // Ekranda hozir turgan son — animatsiya yarmida to'xtasa shundan davom etadi.
  const currentRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!Number.isFinite(target)) return;

    // Harakat kamaytirilgan bo'lsa animatsiya umuman bo'lmaydi.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      currentRef.current = target;
      setValue(target);
      return;
    }

    const from = currentRef.current;
    if (from === target) return;

    const start = performance.now();
    function step(now: number): void {
      const p = Math.min(1, (now - start) / duration);
      // easeOutCubic — boshida tez, oxiriga borib sekinlashadi.
      const next = from + (target - from) * (1 - Math.pow(1 - p, 3));
      currentRef.current = next;
      setValue(next);
      if (p < 1) rafRef.current = requestAnimationFrame(step);
    }
    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration]);

  return value;
}

/**
 * Sanaladigan son. `format` bilan ko'rinishi beriladi (masalan `mlnf`).
 *
 * Ekran o'quvchiga oraliq qiymatlar o'qilmasligi kerak — `aria-hidden` va
 * yonida yakuniy qiymat matn sifatida turadi.
 */
export function CountUp({
  value,
  format,
}: {
  value: number;
  format: (n: number) => string;
}): ReactNode {
  const animated = useCountUp(value);
  return (
    <>
      <span aria-hidden="true">{format(animated)}</span>
      <span className="visually-hidden">{format(value)}</span>
    </>
  );
}

/** Butun sonlar uchun (oila soni, xabar soni va h.k.). */
export function intFormat(n: number): string {
  return String(Math.round(n));
}
