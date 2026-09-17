"use client";

// Grafiklar uchun umumiy sichqoncha-tooltip (har bir chart o'z holatini boshqaradi).

import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type MouseEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

/** Tooltip bilan ekran chekkasi orasida qoldiriladigan bo'shliq. */
const EDGE = 8;
/** Kursordan o'ngga surish; chapga o'girilganda ham shuncha bo'shliq qoladi. */
const OFFSET = 14;

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
    setTip({ x: e.clientX + OFFSET, y: e.clientY - 12, content });
  }
  function hide(): void {
    setTip(null);
  }

  return { tip, show, hide };
}

/**
 * Tooltip `document.body` ga portal orqali chiqariladi.
 *
 * Ilgari u chizilgan joyida — diagramma kartochkasining ichida turardi va ikki
 * xil buzilishga olib kelardi. Sabab: `.card:hover` kartochkaga
 * `transform: translateY(-2px)` beradi, ya'ni tooltipni ko'rish uchun
 * sichqonchani olib borishning o'zi kartochkada yangi "stacking context"
 * hosil qiladi. Natijada:
 *
 *   1. `position: fixed` ekranga emas, o'sha kartochkaga nisbatan
 *      hisoblanadigan bo'lib qolardi — tooltip mutlaqo boshqa joyga
 *      (ekrandan ancha pastga) tushardi;
 *   2. `z-index: 95` faqat kartochka ichida amal qilardi — yonidagi kartochka
 *      tooltipning ustidan chizib, uni yarmidan kesib qo'yardi.
 *
 * `body` da esa hech qanday `transform` yo'q, shuning uchun `fixed` yana
 * ekranga nisbatan ishlaydi va z-index eng yuqori qatlamda solishtiriladi.
 */
export function ChartTooltip({
  tip,
}: {
  tip: { x: number; y: number; content: ReactNode } | null;
}): ReactNode {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  // Portal faqat brauzerda — server renderida `document` yo'q.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* O'lchamni bilmasdan turib chekkaga sig'ishini hisoblab bo'lmaydi, shuning
     uchun avval chiziladi, keyin o'lchanadi va joyi to'g'rilanadi. Bu
     `useLayoutEffect` — brauzer chizishidan OLDIN ishlaydi, ya'ni tooltip
     noto'g'ri joyda bir lahza ham ko'rinmaydi. */
  useLayoutEffect(() => {
    if (!tip || !ref.current) {
      setPos(null);
      return;
    }
    const box = ref.current.getBoundingClientRect();
    const vw = document.documentElement.clientWidth;
    const vh = document.documentElement.clientHeight;

    // O'ngga sig'masa — kursorning chap tomoniga o'tkazamiz.
    let left = tip.x;
    if (left + box.width > vw - EDGE) left = tip.x - OFFSET * 2 - box.width;
    left = Math.max(EDGE, Math.min(left, vw - EDGE - box.width));

    // Pastga sig'masa — yuqoriga suramiz.
    let top = tip.y;
    top = Math.max(EDGE, Math.min(top, vh - EDGE - box.height));

    setPos({ left, top });
  }, [tip]);

  if (!tip || !mounted) return null;

  return createPortal(
    <div
      ref={ref}
      // `on` klassi (opacity: 1) faqat joyi aniqlangach qo'yiladi.
      className={`chart-tip${pos ? " on" : ""}`}
      style={{ left: pos?.left ?? tip.x, top: pos?.top ?? tip.y }}
    >
      {tip.content}
    </div>,
    document.body,
  );
}
