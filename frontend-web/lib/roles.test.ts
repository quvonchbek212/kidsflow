import { describe, expect, it } from "vitest";

import { primaryRole } from "./roles";

describe("primaryRole", () => {
  it("bitta rol bo'lsa o'shani qaytaradi", () => {
    expect(primaryRole([{ role: "TEACHER" }])).toBe("TEACHER");
  });

  it("eng keng huquqli rolni tanlaydi, tartibidan qat'i nazar", () => {
    // Asosiy tekshiruv: ilgari roles[0] olinardi va natija jadvaldan qaysi
    // qator birinchi kelishiga bog'liq edi.
    expect(primaryRole([{ role: "TEACHER" }, { role: "MANAGER" }])).toBe(
      "MANAGER",
    );
    expect(primaryRole([{ role: "MANAGER" }, { role: "TEACHER" }])).toBe(
      "MANAGER",
    );
    expect(primaryRole([{ role: "TEACHER" }, { role: "OWNER" }])).toBe("OWNER");
  });

  it("bo'sh ro'yxatda bo'sh satr qaytaradi", () => {
    expect(primaryRole([])).toBe("");
    expect(primaryRole(null)).toBe("");
    expect(primaryRole(undefined)).toBe("");
  });

  it("noma'lum rolni ma'lumidan past qo'yadi", () => {
    expect(primaryRole([{ role: "NIMADIR" }, { role: "TEACHER" }])).toBe(
      "TEACHER",
    );
  });

  it("faqat noma'lum rollar bo'lsa birinchisini qaytaradi", () => {
    expect(primaryRole([{ role: "NIMADIR" }])).toBe("NIMADIR");
  });
});
