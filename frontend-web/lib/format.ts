// Ko'rsatish uchun formatlash yordamchilari.

export function money(value: string | number): string {
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return String(value);
  // So'm butun sonda ko'rsatiladi — backend NUMERIC(18,2) qaytargani uchun
  // yaxlitlamasak "603,225.806 so'm" kabi qatorlar chiqadi.
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(num) + " so'm";
}

/** Jadval kataklari uchun: faqat raqam, "so'm"siz (mockupdagidek). Valyuta
 *  nomi ustun sarlavhasidan yoki kontekstdan tushunarli, qo'shimcha esa
 *  ustunlarni keraksiz kengaytiradi. */
export function moneyPlain(value: string | number): string {
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(num);
}

export function monthRange(date = new Date()): { start: string; end: string } {
  const year = date.getFullYear();
  const month = date.getMonth();
  const start = new Date(year, month, 1);
  const end = new Date(year, month + 1, 0);
  return { start: isoDate(start), end: isoDate(end) };
}

// Mahalliy sana komponentlaridan tuziladi (`toISOString()` ishlatilmaydi —
// u UTC'ga o'giradi va musbat UTC-offset zonalarda (masalan Toshkent, +5)
// sanani bir kun oldinga suradi, bu esa oy-oralig'i/sana-default xatolariga
// olib keladi).
export function isoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Oxirgi `n` oy (joriy oy bilan tugaydi), har biri uchun {start,end,label}. */
export function lastMonths(n: number, date = new Date()): { start: string; end: string; label: string }[] {
  const out: { start: string; end: string; label: string }[] = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(date.getFullYear(), date.getMonth() - i, 1);
    const { start, end } = monthRange(d);
    out.push({ start, end, label: d.toLocaleDateString("uz-UZ", { month: "short" }) });
  }
  return out;
}

export function mlnf(value: string | number): string {
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return String(value);
  return (num / 1e6).toFixed(1);
}

const MONTH_NAMES: Record<string, string[]> = {
  uz: [
    "Yanvar",
    "Fevral",
    "Mart",
    "Aprel",
    "May",
    "Iyun",
    "Iyul",
    "Avgust",
    "Sentabr",
    "Oktabr",
    "Noyabr",
    "Dekabr",
  ],
  ru: [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
  ],
  en: [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ],
};

/** Davr tugmasidagi yozuv. Oraliq aynan bitta kalendar oy bo'lsa mockupdagi
 *  kabi "Iyul 2026" ko'rinadi, aks holda ikkala sana yoziladi. */
export function periodLabel(start: string, end: string, lang = "uz"): string {
  const from = new Date(start);
  const to = new Date(end);
  if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) return `${start} — ${end}`;
  const monthStart = monthRange(from);
  if (monthStart.start === start && monthStart.end === end) {
    const names = MONTH_NAMES[lang] ?? MONTH_NAMES.uz;
    return `${names[from.getMonth()]} ${from.getFullYear()}`;
  }
  return `${start} — ${end}`;
}

/** Ism-familiyadan avatar uchun ikki harf: "Amirbek Toshmatov" → "AT". */
export function initials(fullName: string): string {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

/** Guruh yosh oralig'i: oylardan yilga ("24–36" → "2–3"). Butun bo'lmasa
 *  bir xona qoldiriladi, chunki 30 oy = 2.5 yosh. */
export function ageRangeLabel(minMonths: number | null, maxMonths: number | null): string {
  if (minMonths == null || maxMonths == null) return "";
  const years = (m: number) => (m % 12 === 0 ? String(m / 12) : (m / 12).toFixed(1));
  return `${years(minMonths)}–${years(maxMonths)}`;
}

const INVOICE_STATUS_UZ: Record<string, string> = {
  OPEN: "To'lanmagan",
  PARTIALLY_PAID: "Qisman to'langan",
  PAID: "To'langan",
  OVERDUE: "Muddati o'tgan",
  CANCELLED: "Bekor qilingan",
  DRAFT: "Qoralama",
};

export function invoiceStatus(status: string): string {
  return INVOICE_STATUS_UZ[status] ?? status;
}

/** Hisob-faktura holatining rang ohangi (mockupdagi `.badge--*`). */
export function invoiceTone(status: string): "pos" | "warn" | "neg" | "mute" {
  if (status === "PAID") return "pos";
  if (status === "PARTIALLY_PAID") return "warn";
  if (status === "OVERDUE" || status === "OPEN") return "neg";
  return "mute";
}
