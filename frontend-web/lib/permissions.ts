/**
 * Rol asosidagi UI ruxsatlari — bitta manba.
 *
 * MUHIM: frontenddagi yashirish xavfsizlik emas. Har bir so'rovni backend
 * mustaqil tekshiradi (`require_roles`, `AccessService`, filial izolyatsiyasi —
 * loyiha strukturasi 2.3-bo'lim). Bu yerdagi matritsaning vazifasi boshqa:
 * foydalanuvchiga bosilganda 403 qaytaradigan tugmani ko'rsatmaslik.
 *
 * Shu sababli matritsa backend qoidasining ko'zgusi bo'lishi kerak. Har bir
 * qobiliyat yonida uni backendda kim tekshirishi izohlangan — qoida
 * o'zgarganda ikkala tomonni birga yangilash uchun.
 *
 * PARENT bu yerda yo'q: ota-onalar web panelga kirmaydi, ular Telegram bot
 * orqali ishlaydi (7-bo'lim).
 */

export type Role = "OWNER" | "MANAGER" | "TEACHER";

export type Capability =
  /** Bosh sahifa: KPI va diagrammalar. Backend: analytics.py — OWNER/MANAGER. */
  | "dashboard.view"
  /** To'lovlar, xarajatlar, moliyaviy hisobotlar. Backend: billing/expenses — OWNER/MANAGER. */
  | "finance.view"
  /** Bolalar ro'yxatini ko'rish. TEACHER faqat o'z guruhidagilarni ko'radi
   *  (bu chegarani backend AccessService qo'yadi, UI emas). */
  | "children.view"
  /** Bola qo'shish/tahrirlash, qabul (enrollment) boshqaruvi. */
  | "children.manage"
  /** Guruhlar bo'limi. */
  | "groups.manage"
  /** Davomat belgilash. Backend: AccessService.can_mark_attendance_for_child. */
  | "attendance.mark"
  /** Kunlik hisobot yozish. */
  | "reports.write"
  /** Xodimlar ro'yxati. Backend: users.py GET — OWNER/MANAGER (menejer o'z filiali). */
  | "staff.view"
  /** Xodim yaratish/tahrirlash. Menejer o'z filialida; OWNER hisobiga tegib bo'lmaydi. */
  | "staff.manage"
  /** Maosh belgilash va ish haqi fondi. Backend: users.py PATCH salary, payroll. */
  | "salary.edit"
  /** Ota-onalar bo'limi va ularga xabar. Backend: messages.py — OWNER/MANAGER. */
  | "parents.message"
  /** Sozlamalar bo'limi. Backend: settings_service.update — faqat OWNER. */
  | "settings.view"
  /** Filial yaratish/tahrirlash. Backend: branches.py — faqat OWNER. */
  | "branches.manage";

/**
 * Rol → qobiliyatlar.
 *
 * OWNER — bog'cha egasi, hammasi ochiq.
 *
 * MANAGER — filialning kundalik ishini olib boradi: bolalar, guruhlar, davomat,
 * moliya, xodimlar. Filial doirasini backend qo'yadi. Sozlamalar va filial
 * boshqaruvi unga berilmagan — bular butun bog'chaga taalluqli qarorlar.
 *
 * TEACHER — o'z guruhi bilan ishlaydi: davomat, kunlik hisobot va guruhidagi
 * bolalar ro'yxati (faqat ko'rish).
 */
const MATRIX: Record<Role, readonly Capability[]> = {
  OWNER: [
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
  ],
  MANAGER: [
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
  ],
  TEACHER: ["children.view", "attendance.mark", "reports.write"],
};

function isKnownRole(role: string): role is Role {
  return role in MATRIX;
}

/**
 * Rolda shu qobiliyat bormi.
 *
 * Noma'lum rol (bo'sh satr — foydalanuvchi hali yuklanmagan, yoki kelajakda
 * qo'shiladigan rol) hech narsa ko'rmaydi. Bu ataylab: interfeys yuklanish
 * paytida keraksiz bo'limni bir lahzaga ko'rsatib yubormaydi.
 */
export function can(role: string, capability: Capability): boolean {
  return isKnownRole(role) && MATRIX[role].includes(capability);
}

/** Rol umuman web panelga kiradimi (PARENT kirmaydi). */
export function isWebRole(role: string): role is Role {
  return isKnownRole(role);
}

/**
 * Rol tizimga kirgach tushadigan sahifa.
 *
 * Menyudagi birinchi bandni olish yetarli emas edi: menyu tartibi mockupga
 * qarab qat'iy (Bosh sahifa → Bolalar → ...), tarbiyachining kundalik ishi esa
 * davomat. Shuning uchun uy sahifasi ochiq belgilanadi.
 */
const HOME_HREF: Record<Role, string> = {
  OWNER: "/dashboard",
  MANAGER: "/dashboard",
  TEACHER: "/attendance",
};

export function homeHrefFor(role: string): string | null {
  return isKnownRole(role) ? HOME_HREF[role] : null;
}
