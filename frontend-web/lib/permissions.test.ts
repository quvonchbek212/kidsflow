/**
 * Qobiliyat matritsasi testlari.
 *
 * Bu yerda tekshiriladigan narsa — matritsa backend qoidasiga mos turishi.
 * Test o'zi backendni chaqirmaydi (u alohida `pytest` bilan tekshiriladi);
 * vazifasi — qoida beixtiyor o'zgarib ketsa (masalan yangi qobiliyat hamma
 * rolga nusxalansa) buni darrov ko'rsatish.
 */

import { describe, expect, it } from "vitest";

import { can, homeHrefFor, isWebRole, type Capability } from "./permissions";

describe("can()", () => {
  it("egasiga hamma narsa ochiq", () => {
    const all: Capability[] = [
      "dashboard.view",
      "finance.view",
      "children.view",
      "children.manage",
      "groups.manage",
      "attendance.mark",
      "reports.write",
      "staff.view",
      "staff.manage",
      "salary.edit",
      "parents.message",
      "settings.view",
      "branches.manage",
    ];
    for (const capability of all) {
      expect(can("OWNER", capability)).toBe(true);
    }
  });

  it("menejer xodimlarni boshqaradi, lekin sozlamalar va filialga tegmaydi", () => {
    expect(can("MANAGER", "staff.view")).toBe(true);
    expect(can("MANAGER", "staff.manage")).toBe(true);
    expect(can("MANAGER", "salary.edit")).toBe(true);
    expect(can("MANAGER", "finance.view")).toBe(true);

    expect(can("MANAGER", "settings.view")).toBe(false);
    expect(can("MANAGER", "branches.manage")).toBe(false);
  });

  it("tarbiyachi faqat o'z guruhi ishini bajaradi", () => {
    expect(can("TEACHER", "attendance.mark")).toBe(true);
    expect(can("TEACHER", "reports.write")).toBe(true);
    expect(can("TEACHER", "children.view")).toBe(true);

    // Ko'rish huquqi tahrirlash huquqini bermaydi.
    expect(can("TEACHER", "children.manage")).toBe(false);
    expect(can("TEACHER", "finance.view")).toBe(false);
    expect(can("TEACHER", "staff.view")).toBe(false);
    expect(can("TEACHER", "salary.edit")).toBe(false);
    expect(can("TEACHER", "settings.view")).toBe(false);
  });

  it("noma'lum yoki hali yuklanmagan rol hech narsa ko'rmaydi", () => {
    // Ota-onalar web panelga kirmaydi (Telegram orqali ishlaydi).
    expect(can("PARENT", "children.view")).toBe(false);
    // Foydalanuvchi hali yuklanmaganda rol bo'sh satr bo'ladi.
    expect(can("", "attendance.mark")).toBe(false);
    expect(can("ADMIN", "settings.view")).toBe(false);
  });
});

describe("homeHrefFor()", () => {
  it("tarbiyachini davomatga, qolganlarni bosh sahifaga yuboradi", () => {
    expect(homeHrefFor("OWNER")).toBe("/dashboard");
    expect(homeHrefFor("MANAGER")).toBe("/dashboard");
    expect(homeHrefFor("TEACHER")).toBe("/attendance");
  });

  it("noma'lum rol uchun manzil yo'q", () => {
    expect(homeHrefFor("PARENT")).toBeNull();
    expect(homeHrefFor("")).toBeNull();
  });
});

describe("isWebRole()", () => {
  it("faqat panelga kiradigan uchta rolni tan oladi", () => {
    expect(isWebRole("OWNER")).toBe(true);
    expect(isWebRole("MANAGER")).toBe(true);
    expect(isWebRole("TEACHER")).toBe(true);
    expect(isWebRole("PARENT")).toBe(false);
  });
});
