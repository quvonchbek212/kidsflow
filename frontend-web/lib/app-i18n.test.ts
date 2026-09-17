import { describe, expect, it } from "vitest";

import { APP_I18N } from "./app-i18n";
import type { Lang } from "./lang";

const LANGS: Lang[] = ["uz", "ru", "en"];

/** Obyektni rekursiv aylanib, barcha satr kalitlarini yig'adi. */
function collect(value: unknown, prefix = ""): Map<string, string> {
  const out = new Map<string, string>();
  if (typeof value === "string") {
    out.set(prefix, value);
    return out;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      for (const [k, v] of collect(child, prefix ? `${prefix}.${key}` : key)) {
        out.set(k, v);
      }
    }
  }
  return out;
}

describe("app-i18n", () => {
  it("uchala til ham qurilgan", () => {
    // `pick()` yetishmagan kalitda xato tashlaydi — modul import qilinishining
    // o'zi tarjima qo'shishda unutilgan kalitni ushlaydi.
    for (const lang of LANGS) {
      expect(APP_I18N[lang]).toBeTruthy();
    }
  });

  it("uchala tilda ham bir xil kalitlar to'plami bor", () => {
    const [uz, ru, en] = LANGS.map((l) => collect(APP_I18N[l]));
    expect([...ru.keys()].sort()).toEqual([...uz.keys()].sort());
    expect([...en.keys()].sort()).toEqual([...uz.keys()].sort());
  });

  it("birorta tarjima bo'sh emas", () => {
    for (const lang of LANGS) {
      const empty = [...collect(APP_I18N[lang])]
        .filter(([, v]) => v.trim() === "")
        .map(([k]) => k);
      expect(empty, `${lang}: bo'sh tarjimalar`).toEqual([]);
    }
  });

  it("ruscha va inglizcha matnlar o'zbekchadan farq qiladi", () => {
    // To'liq farq talab qilinmaydi (masalan "KIDSFLOW" hamma tilda bir xil),
    // lekin ko'pchiligi tarjima qilingan bo'lishi kerak — aks holda kimdir
    // kalitni uch marta nusxalab qo'ygan bo'ladi.
    const uz = collect(APP_I18N.uz);
    const ru = collect(APP_I18N.ru);
    let same = 0;
    for (const [key, value] of uz) {
      if (ru.get(key) === value) same += 1;
    }
    expect(same / uz.size).toBeLessThan(0.35);
  });
});
