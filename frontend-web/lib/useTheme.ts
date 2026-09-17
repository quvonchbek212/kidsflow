"use client";

import { useCallback, useEffect, useState } from "react";

const KEY = "kidsflow_theme";

/**
 * Yorug'/tungi mavzu.
 *
 * Atributni birinchi chizilishdan oldin `app/layout.tsx` dagi inline skript
 * qo'yadi — bu hook faqat React holatini shunga moslaydi va almashtirishni
 * beradi. Ilgari bu mantiq AppShell ichida edi, lekin kirish sahifalari
 * qobiqsiz chiziladi (`AppChrome` ularni `BARE` deb belgilaydi), shuning
 * uchun umumiy joyga chiqarildi.
 */
export function useTheme(): { dark: boolean; toggle: () => void } {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.getAttribute("data-theme") === "dark");
  }, []);

  // Foydalanuvchi o'zi tanlamagan bo'lsa, OS sozlamasi o'zgarganda ergashamiz.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    function onChange(e: MediaQueryListEvent): void {
      if (window.localStorage.getItem(KEY)) return;
      document.documentElement.setAttribute(
        "data-theme",
        e.matches ? "dark" : "light",
      );
      setDark(e.matches);
    }
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const toggle = useCallback(() => {
    setDark((prev) => {
      const next = !prev;
      // Atribut har doim aniq qiymat bilan qo'yiladi: OS tungi rejimda bo'lsa
      // ham qo'lda tanlangan yorug' keyingi yuklashda saqlanadi.
      document.documentElement.setAttribute(
        "data-theme",
        next ? "dark" : "light",
      );
      window.localStorage.setItem(KEY, next ? "dark" : "light");
      return next;
    });
  }, []);

  return { dark, toggle };
}
