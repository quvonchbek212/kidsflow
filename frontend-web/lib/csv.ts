// Brauzerda CSV yasab yuklab berish. Backendda eksport endpointi yo'q,
// shuning uchun hisobot ekranda bor ma'lumotdan tuziladi.

function cell(value: string | number): string {
  let s = String(value ?? "");
  // Formula injeksiyasi: `=`, `+`, `-`, `@` bilan boshlanadigan matn Excel'da
  // formula sifatida ishga tushadi (masalan, guruh nomi `=HYPERLINK(...)`).
  // Apostrof uni oddiy matnga aylantiradi. Sonlar tegilmaydi (manfiy summa).
  if (typeof value === "string" && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  // Excel `;` bilan ajratilgan faylni mahalliy sozlamada to'g'ri ochadi,
  // qo'shtirnoq ichidagi qo'shtirnoq esa ikkilantiriladi.
  return /[";\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Qatorlarni Excel uchun `;` bilan ajratilgan CSV matniga aylantiradi. */
export function toCsv(rows: (string | number)[][]): string {
  return rows.map((r) => r.map(cell).join(";")).join("\r\n");
}

export function downloadCsv(
  filename: string,
  rows: (string | number)[][],
): void {
  const body = toCsv(rows);
  // BOM — Excel faylni UTF-8 deb tanishi uchun (kirill/o'zbek harflari).
  const blob = new Blob(["﻿" + body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Darhol bekor qilinsa, Safari/Firefox yuklab olishni boshlashga ulgurmay
  // qolishi mumkin.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
