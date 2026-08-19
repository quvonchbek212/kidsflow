// Brauzerda CSV yasab yuklab berish. Backendda eksport endpointi yo'q,
// shuning uchun hisobot ekranda bor ma'lumotdan tuziladi.

function cell(value: string | number): string {
  const s = String(value ?? "");
  // Excel `;` bilan ajratilgan faylni mahalliy sozlamada to'g'ri ochadi,
  // qo'shtirnoq ichidagi qo'shtirnoq esa ikkilantiriladi.
  return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function downloadCsv(
  filename: string,
  rows: (string | number)[][],
): void {
  const body = rows.map((r) => r.map(cell).join(";")).join("\r\n");
  // BOM — Excel faylni UTF-8 deb tanishi uchun (kirill/o'zbek harflari).
  const blob = new Blob(["﻿" + body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
