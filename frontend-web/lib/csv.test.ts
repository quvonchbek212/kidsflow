import { describe, expect, it } from "vitest";

import { toCsv } from "./csv";

describe("toCsv", () => {
  it("formula bilan boshlanadigan matnni oddiy matnga aylantiradi", () => {
    const out = toCsv([['=HYPERLINK("http://x")', "+1", "-2", "@SUM(A1)"]]);
    expect(out).toBe(`"'=HYPERLINK(""http://x"")";'+1;'-2;'@SUM(A1)`);
  });

  it("sonlarga tegmaydi (manfiy summa formula emas)", () => {
    expect(toCsv([["Qoldiq", -500000]])).toBe("Qoldiq;-500000");
  });

  it("ajratgich, qo'shtirnoq va qator uzilishini qo'shtirnoqqa oladi", () => {
    expect(toCsv([["a;b", 'x"y', "1\r\n2"]])).toBe('"a;b";"x""y";"1\r\n2"');
  });
});
