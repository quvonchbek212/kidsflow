import { describe, expect, it } from "vitest";

import { isoDate, lastMonths, monthRange, moneyPlain, money } from "./format";

describe("money", () => {
  it("so'mni butun sonda ko'rsatadi", () => {
    // Backend NUMERIC(18,2) qaytaradi; yaxlitlanmasa "603,225.81 so'm" chiqardi.
    expect(money("1500000.00")).toContain("so'm");
    expect(money("1500000.00")).not.toContain(",00");
    expect(money("1500000.00")).not.toContain(".00");
  });

  it("kasr qismini yaxlitlaydi", () => {
    expect(moneyPlain("603225.806")).not.toContain(".");
  });

  it("son bo'lmagan qiymatni o'zgartirmay qaytaradi", () => {
    expect(money("—")).toBe("—");
    expect(moneyPlain("yo'q")).toBe("yo'q");
  });

  it("nolni to'g'ri ko'rsatadi", () => {
    expect(moneyPlain(0)).toBe("0");
  });
});

describe("isoDate", () => {
  it("mahalliy sana komponentlaridan tuziladi", () => {
    // Asosiy tekshiruv: toISOString() UTC'ga o'girib, Toshkentda (UTC+5)
    // kunni bir kun orqaga surardi. Mahalliy vaqt bo'yicha 1-yanvar 02:00
    // UTC'da hali 31-dekabr — sana "2026-01-01" bo'lib qolishi shart.
    const localNewYearEarlyMorning = new Date(2026, 0, 1, 2, 0, 0);
    expect(isoDate(localNewYearEarlyMorning)).toBe("2026-01-01");
  });

  it("oy va kunni ikki xonali qiladi", () => {
    expect(isoDate(new Date(2026, 2, 5))).toBe("2026-03-05");
  });
});

describe("monthRange", () => {
  it("oyning birinchi va oxirgi kunini beradi", () => {
    expect(monthRange(new Date(2026, 1, 15))).toEqual({
      start: "2026-02-01",
      end: "2026-02-28",
    });
  });

  it("kabisa yilini hisobga oladi", () => {
    expect(monthRange(new Date(2028, 1, 10)).end).toBe("2028-02-29");
  });

  it("31 kunli oyni to'g'ri yopadi", () => {
    expect(monthRange(new Date(2026, 0, 9)).end).toBe("2026-01-31");
  });
});

describe("lastMonths", () => {
  it("joriy oy bilan tugaydigan n ta oy qaytaradi", () => {
    const months = lastMonths(3, new Date(2026, 2, 15));
    expect(months).toHaveLength(3);
    expect(months[0].start).toBe("2026-01-01");
    expect(months[2].start).toBe("2026-03-01");
  });

  it("yil chegarasidan orqaga o'tadi", () => {
    const months = lastMonths(3, new Date(2026, 0, 15));
    expect(months[0].start).toBe("2025-11-01");
    expect(months[2].start).toBe("2026-01-01");
  });
});
