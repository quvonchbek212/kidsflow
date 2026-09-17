"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { CommandPalette, type CommandItem } from "@/components/CommandPalette";
import {
  IconBell,
  IconBuilding,
  IconCalendar,
  IconChat,
  IconCheck,
  IconChevronDown,
  IconCollapse,
  IconEdit,
  IconGrid,
  IconMenu,
  IconMessage,
  IconMoon,
  IconReceipt,
  IconSearch,
  IconSettings,
  IconSun,
  IconTrendingDown,
  IconUser,
  IconUsers,
  IconWallet,
} from "@/components/icons";
import {
  LoadError,
  logSecondaryFailure,
  recoverWith,
} from "@/components/ui/LoadError";
import { useModal } from "@/components/ui/ModalProvider";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { APP_I18N, type AppStrings } from "@/lib/app-i18n";
import {
  ApiError,
  api,
  type Branch,
  type CurrentUser,
  type Group,
} from "@/lib/api";
import {
  initials,
  isoDate,
  money,
  monthRange,
  periodLabel,
} from "@/lib/format";
import type { Lang } from "@/lib/lang";
import { can, homeHrefFor, type Capability } from "@/lib/permissions";
import { primaryRole } from "@/lib/roles";
import { useTheme } from "@/lib/useTheme";

/** Xabarlar sahifasi suhbatni o'qilgan deb belgilaganda yuboradi. */
export const MESSAGES_READ_EVENT = "kidsflow:messages-read";
const NOTIF_READ_KEY = "kidsflow_notif_read";

interface NotifItem {
  key: string;
  /* O'qilgan deb belgilash shu imzo bo'yicha eslab qolinadi. Unga holat
     kiradi (qarz summasi, savollar soni) — vaziyat o'zgarsa bildirishnoma
     yana chiqadi, aks holda yangi qarz ham "o'qilgan" bo'lib yashirinardi. */
  sig: string;
  href: string;
  title: string;
  sub: string;
  tone: "neg" | "warn";
  icon: ReactNode;
}

export interface Period {
  start: string;
  end: string;
}

interface PageMeta {
  title?: string;
  subtitle?: string;
  /** Qaysi manzil uchun berilgani. Eski bo'limning sarlavhasi yangi sahifada
   *  ko'rinib qolmasligi uchun ishlatiladi — pastdagi izohga qarang. */
  path?: string;
}

interface AppUI {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: AppStrings;
  branches: Branch[];
  branchId: string;
  setBranchId: (id: string) => void;
  period: Period;
  setPeriod: (p: Period) => void;
  /** Sahifa o'z sarlavha/izohini topbarga beradi — mockupdagidek sarlavha
   *  faqat bir joyda (topbarda) turadi, kontent ichida takrorlanmaydi. */
  setPageMeta: (meta: PageMeta) => void;
  /** Joriy foydalanuvchining amaldagi roli. */
  role: string;
  /** Sahifa ichidagi tugmalarni yashirish uchun: `can("staff.manage")`.
   *  Menyuni AppShell o'zi filtrlaydi, kontent esa buni ishlatadi — aks holda
   *  ko'rish huquqi bor foydalanuvchiga tahrirlash tugmasi ham ko'rinardi. */
  can: (capability: Capability) => boolean;
}

const AppUIContext = createContext<AppUI | null>(null);

export function useAppUI(): AppUI {
  const ctx = useContext(AppUIContext);
  if (!ctx) throw new Error("useAppUI AppShell ichida ishlatilishi kerak");
  return ctx;
}

const LANGS: Lang[] = ["uz", "ru", "en"];
// Mockupda tillar to'liq nomi bilan yoziladi, qisqartma bilan emas.
const LANG_LABEL: Record<Lang, string> = {
  uz: "O'zbekcha",
  ru: "Русский",
  en: "English",
};

export type NavKey =
  | "dashboard"
  | "reports"
  | "dailyReports"
  | "children"
  | "groups"
  | "attendance"
  | "staff"
  | "payments"
  | "expenses"
  | "parents"
  | "inbox"
  | "settings";

type Section = "general" | "kindergarten" | "finance" | "other";

interface NavItem {
  key: NavKey;
  href: string;
  section: Section;
  icon: (size?: number) => ReactNode;
  /** Bandni ko'rish uchun kerakli qobiliyat (`lib/permissions.ts`). */
  capability: Capability;
}

// Tartib mockupdagi bilan bir xil: Umumiy → Bog'cha → Moliya → Boshqa.
const NAV_ITEMS: NavItem[] = [
  {
    key: "dashboard",
    href: "/dashboard",
    section: "general",
    capability: "dashboard.view",
    icon: (s) => <IconGrid size={s} />,
  },
  {
    key: "reports",
    href: "/finance/reports",
    section: "general",
    capability: "finance.view",
    icon: (s) => <IconReceipt size={s} />,
  },
  {
    key: "children",
    href: "/children",
    section: "kindergarten",
    capability: "children.view",
    icon: (s) => <IconUsers size={s} />,
  },
  {
    key: "groups",
    href: "/groups",
    section: "kindergarten",
    capability: "groups.manage",
    icon: (s) => <IconBuilding size={s} />,
  },
  {
    key: "attendance",
    href: "/attendance",
    section: "kindergarten",
    capability: "attendance.mark",
    icon: (s) => <IconCalendar size={s} />,
  },
  {
    key: "dailyReports",
    href: "/daily-reports",
    section: "kindergarten",
    capability: "reports.write",
    icon: (s) => <IconEdit size={s} />,
  },
  {
    key: "staff",
    href: "/staff",
    section: "kindergarten",
    capability: "staff.view",
    icon: (s) => <IconUser size={s} />,
  },
  {
    key: "payments",
    href: "/billing",
    section: "finance",
    capability: "finance.view",
    icon: (s) => <IconWallet size={s} />,
  },
  {
    key: "expenses",
    href: "/finance/expenses",
    section: "finance",
    capability: "finance.view",
    icon: (s) => <IconTrendingDown size={s} />,
  },
  {
    key: "inbox",
    href: "/messages",
    section: "other",
    capability: "parents.message",
    icon: (s) => <IconChat size={s} />,
  },
  {
    key: "parents",
    href: "/parents",
    section: "other",
    capability: "parents.message",
    icon: (s) => <IconMessage size={s} />,
  },
  {
    key: "settings",
    href: "/settings",
    section: "other",
    capability: "settings.view",
    icon: (s) => <IconSettings size={s} />,
  },
];

const SECTIONS: Section[] = ["general", "kindergarten", "finance", "other"];

/**
 * Rol ko'radigan menyu bandlari.
 *
 * Ilgari bu yerda tarbiyachi uchun qo'lda yozilgan kalitlar ro'yxati turardi,
 * OWNER va MANAGER esa bir xil to'liq menyu olardi — ya'ni menejer ochib
 * bo'lmaydigan bo'limlarni ko'rar va bosganda 403 olardi. Endi manba bitta:
 * `lib/permissions.ts` dagi matritsa. Yangi sahifa qo'shilganda faqat unga
 * qobiliyat berish kifoya, bu yerni yangilash esdan chiqmaydi.
 */
function navForRole(role: string): NavItem[] {
  return NAV_ITEMS.filter((item) => can(role, item.capability));
}

/** Rol uchun boshlang'ich sahifa; noma'lum rolda menyudagi birinchi band. */
function firstHrefForRole(role: string): string {
  return homeHrefFor(role) ?? navForRole(role)[0]?.href ?? "/attendance";
}

/** "Mening profilim" oynasi — faqat F.I.O. va telefon.
 *
 *  Til bu yerda emas: u foydalanuvchi menyusida allaqachon bor. Rol, email va
 *  maosh esa OWNER huquqida qoladi — `PATCH /auth/me` sxemasi ularni umuman
 *  qabul qilmaydi. */
function ProfileForm({
  user,
  t,
  onSaved,
}: {
  user: CurrentUser;
  t: AppStrings;
  onSaved: (updated: CurrentUser) => void;
}): ReactNode {
  const [fullName, setFullName] = useState(user.full_name);
  const [phone, setPhone] = useState(user.phone ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent): Promise<void> {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateProfile({
        full_name: fullName.trim(),
        phone: phone.trim() || null,
      });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.common.errTitle);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <label className="field">
        <span className="field__label">{t.common.fullName}</span>
        <input
          className="input"
          required
          maxLength={255}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
      </label>
      <label className="field">
        <span className="field__label">{t.common.phone}</span>
        <input
          className="input"
          placeholder="+998 90 123 45 67"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
      </label>

      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn btn--full" type="submit" disabled={saving}>
        {saving ? t.common.saving : t.common.save}
      </button>
    </form>
  );
}

/** Davr tanlash oynasi. Modal ichida o'z holatini boshqaradi, shuning uchun
 *  alohida komponent (ModalProvider faqat bir marta "suratga oladi"). */
function PeriodForm({
  initial,
  t,
  onApply,
}: {
  initial: Period;
  t: AppStrings;
  onApply: (p: Period) => void;
}): ReactNode {
  const [draft, setDraft] = useState<Period>(initial);

  function quick(kind: "this" | "prev" | "quarter" | "year"): void {
    const now = new Date();
    if (kind === "this") setDraft(monthRange(now));
    else if (kind === "prev")
      setDraft(monthRange(new Date(now.getFullYear(), now.getMonth() - 1, 1)));
    else if (kind === "quarter") {
      const q = Math.floor(now.getMonth() / 3);
      setDraft({
        start: isoDate(new Date(now.getFullYear(), q * 3, 1)),
        end: isoDate(new Date(now.getFullYear(), q * 3 + 3, 0)),
      });
    } else
      setDraft({
        start: isoDate(new Date(now.getFullYear(), 0, 1)),
        end: isoDate(new Date(now.getFullYear(), 11, 31)),
      });
  }

  const quickItems: [string, "this" | "prev" | "quarter" | "year"][] = [
    [t.common.thisMonth, "this"],
    [t.common.prevMonth, "prev"],
    [t.common.quarter, "quarter"],
    [t.common.year, "year"],
  ];
  const active = (kind: "this" | "prev" | "quarter" | "year"): boolean => {
    const now = new Date();
    if (kind === "this") {
      const r = monthRange(now);
      return r.start === draft.start && r.end === draft.end;
    }
    if (kind === "prev") {
      const r = monthRange(new Date(now.getFullYear(), now.getMonth() - 1, 1));
      return r.start === draft.start && r.end === draft.end;
    }
    return false;
  };

  return (
    <>
      {/* Tugmalar guruhi — `<label>` bitta boshqaruv elementiga bog'lanadi,
          shuning uchun bu yerda guruh sarlavhasi ishlatiladi. */}
      <div className="field" role="group" aria-labelledby="period-quick-label">
        <span className="field__label" id="period-quick-label">
          {t.common.quickPick}
        </span>
        <div className="segmented">
          {quickItems.map(([label, kind]) => (
            <button
              key={kind}
              type="button"
              aria-pressed={active(kind)}
              className={active(kind) ? "on" : ""}
              onClick={() => quick(kind)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="form-grid">
        <label className="field">
          <span className="field__label">{t.common.from}</span>
          <input
            className="input"
            type="date"
            value={draft.start}
            onChange={(e) => setDraft((d) => ({ ...d, start: e.target.value }))}
          />
        </label>
        <label className="field">
          <span className="field__label">{t.common.to}</span>
          <input
            className="input"
            type="date"
            value={draft.end}
            onChange={(e) => setDraft((d) => ({ ...d, end: e.target.value }))}
          />
        </label>
      </div>
      <button
        type="button"
        className="btn btn--full"
        onClick={() => onApply(draft)}
      >
        {t.common.apply}
      </button>
    </>
  );
}

export function AppShell({
  user,
  active,
  requires,
  title,
  subtitle,
  children,
}: {
  user: CurrentUser | null;
  active?: NavKey;
  /** Menyuda bandi yo'q sahifalar uchun qo'riqchi (masalan oziq-ovqat
   *  bo'limi). `active` beriladigan sahifalarda qobiliyat menyu bandidan
   *  olinadi, bu yerda esa ochiq ko'rsatiladi. */
  requires?: Capability;
  title?: string;
  subtitle?: string;
  children: ReactNode;
}): ReactNode {
  const router = useRouter();
  const pathname = usePathname();
  // Bosilgan, lekin hali ochilmagan bo'lim. Sahifalar `force-dynamic` (CSP
  // nonce sababli), ya'ni bosgandan keyin serverdan javob kutiladi. Next'ning
  // `loading.tsx` chegarasi faqat marshrut oldindan yuklangan bo'lsa darhol
  // ko'rinadi — `next dev` da prefetch yo'q. Shuning uchun javobni o'zimiz
  // beramiz: bosish zahoti kontent o'rniga skelet chiziladi.
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  const [showPending, setShowPending] = useState(false);
  const modal = useModal();
  const [lang, setLangState] = useState<Lang>("uz");
  // Mavzu mantiqi kirish sahifalari bilan umumiy (ular qobiqsiz chiziladi).
  const { dark, toggle: toggleTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const [notifs, setNotifs] = useState<NotifItem[]>([]);
  // O'qilmagan savollar alohida saqlanadi va alohida (tez-tez) so'raladi:
  // qolgan bildirishnomalar og'ir agregatlardan hisoblanadi, bu esa yengil
  // sanoq va ota-ona yozganda darhol ko'rinishi kerak.
  const [unreadQuestions, setUnreadQuestions] = useState(0);
  const [counts, setCounts] = useState<Partial<Record<NavKey, number>>>({});
  const [pageMeta, setPageMetaState] = useState<PageMeta>({});
  const menuRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const [branchOpen, setBranchOpen] = useState(false);
  const branchRef = useRef<HTMLDivElement>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [kindergartenName, setKindergartenName] = useState("");
  const [branchId, setBranchIdState] = useState("");
  const [branchesError, setBranchesError] = useState<unknown>(null);
  const [period, setPeriodState] = useState<Period>(() => monthRange());

  // Filiallar ro'yxati butun ilova uchun kalit: sahifalar `branchId`
  // aniqlanmaguncha so'rov yubormaydi. Shuning uchun bu so'rov yiqilsa
  // xatoni ko'rsatish shart — aks holda sahifalar abadiy "yuklanmoqda"
  // holatida qotib qolardi va sabab ko'rinmasdi.
  const loadBranches = useCallback((): void => {
    setBranchesError(null);
    api.listBranches().then(setBranches).catch(setBranchesError);
  }, []);

  useEffect(loadBranches, [loadBranches]);

  useEffect(() => {
    // Yon panel sarlavhasi bog'cha nomini ko'rsatadi (filial nomini emas) —
    // u Sozlamalar sahifasida kiritiladi.
    api
      .getSettings()
      .then((s) => setKindergartenName(s.name))
      .catch(logSecondaryFailure("Bog'cha nomi"));
    const saved = window.localStorage.getItem("kidsflow_branch_id");
    if (saved) setBranchIdState(saved);
  }, []);

  function setBranchId(id: string): void {
    setBranchIdState(id);
    window.localStorage.setItem("kidsflow_branch_id", id);
  }

  const setPeriod = useCallback((p: Period) => setPeriodState(p), []);

  /* Sahifa bergan sarlavha QAYSI manzil uchun ekani bilan birga saqlanadi.
     Ilgari eski qiymatni `pathname` o'zgarganda alohida effekt tozalardi,
     lekin React'da BOLA komponentning effekti OTA effektidan oldin ishlaydi:
     yangi sahifa mount bo'lib o'z sarlavhasini beradi → keyin AppShell'ning
     effekti uni darhol o'chirardi. Natijada sahifa izohi (`subtitle`) hech
     qachon ko'rinmasdi — sarlavhaning o'zi menyu bandidan zaxira qiymat
     olgani uchun bu sezilmay qolgan edi.
     Endi tozalash kerak emas: manzili mos kelmagan qiymat o'zi e'tiborsiz
     qoladi. `pathname` ref orqali olinadi, chunki bu funksiya bir marta
     yaratiladi va closure'dagi qiymat eskirib qolardi. */
  const pathnameRef = useRef(pathname);
  pathnameRef.current = pathname;

  // Bir xil qiymat qayta yozilib, cheksiz render tsikliga tushmasligi uchun
  // faqat haqiqatan o'zgarganda holat yangilanadi.
  const setPageMeta = useCallback((meta: PageMeta) => {
    setPageMetaState((prev) =>
      prev.title === meta.title &&
      prev.subtitle === meta.subtitle &&
      prev.path === pathnameRef.current
        ? prev
        : { ...meta, path: pathnameRef.current },
    );
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent): void {
      if (
        menuOpen &&
        menuRef.current &&
        !menuRef.current.contains(e.target as Node)
      ) {
        setMenuOpen(false);
      }
      if (
        notifOpen &&
        notifRef.current &&
        !notifRef.current.contains(e.target as Node)
      ) {
        setNotifOpen(false);
      }
      if (
        branchOpen &&
        branchRef.current &&
        !branchRef.current.contains(e.target as Node)
      ) {
        setBranchOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen, notifOpen, branchOpen]);

  // Sidebar yig'ilgan holati `body` klassiga yoziladi (CSS shunga tayanadi).
  useEffect(() => {
    document.body.classList.toggle("collapsed", collapsed);
    return () => document.body.classList.remove("collapsed");
  }, [collapsed]);

  useEffect(() => {
    const savedLang = window.localStorage.getItem(
      "kidsflow_lang",
    ) as Lang | null;
    if (savedLang) setLangState(savedLang);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent): void {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdkOpen(true);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function setLang(l: Lang): void {
    setLangState(l);
    window.localStorage.setItem("kidsflow_lang", l);
  }

  async function logout(): Promise<void> {
    await api.logout();
    router.replace("/login");
  }

  const t = APP_I18N[lang];
  const role = primaryRole(user?.roles);
  // Sahifalar buni effekt bog'liqliklarida ishlatadi (masalan qaysi so'rovni
  // umuman yubormaslikni hal qilishda) — har renderda yangi funksiya bo'lsa
  // ular cheksiz qayta yuklanardi.
  useEffect(() => {
    setPendingHref(null);
    setShowPending(false);
    /* Sarlavhani bu yerda tozalash SHART EMAS: `pageMeta` o'z manzilini
       saqlaydi va mos kelmasa quyida e'tiborsiz qoldiriladi. Ilgari shu
       yerda `setPageMetaState({})` turardi va u yangi sahifa endigina bergan
       sarlavhani o'chirib yuborardi (bola effekti ota effektidan oldin
       ishlaydi). */
  }, [pathname]);

  // Skelet darhol emas, qisqa kechikish bilan chiziladi: tez o'tishlarda
  // (production'da ~70ms) u umuman ko'rinmaydi va chaqnash bo'lmaydi; sekin
  // bo'lsa esa foydalanuvchi bosish qabul qilinganini ko'radi. Ikkinchi
  // taymer — navigatsiya bekor bo'lsa skelet abadiy qolib ketmasligi uchun.
  useEffect(() => {
    if (pendingHref === null) return;
    const show = window.setTimeout(() => setShowPending(true), 120);
    const bail = window.setTimeout(() => {
      setPendingHref(null);
      setShowPending(false);
    }, 8000);
    return () => {
      window.clearTimeout(show);
      window.clearTimeout(bail);
    };
  }, [pendingHref]);

  const canForRole = useCallback(
    (capability: Capability) => can(role, capability),
    [role],
  );
  const roleLabel = t.roleLabels[role] ?? role;
  const displayName = user?.full_name || user?.username || "";
  const userInitials = initials(displayName || "U");

  const userBranchId = user?.roles?.find((r) => r.branch_id)?.branch_id ?? null;
  const canSwitchBranch = userBranchId === null && branches.length > 1;

  useEffect(() => {
    if (branches.length === 0) return;
    if (branchId && branches.some((b) => b.id === branchId)) return;
    const fallback = userBranchId ?? branches[0]?.id ?? "";
    if (fallback) setBranchId(fallback);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [branches, userBranchId]);

  const branch = branches.find((b) => b.id === branchId);
  const branchName = branch?.name || "KIDSFLOW";
  // Sozlamalar hali yuklanmagan bo'lsa filial nomiga qaytamiz — sarlavha
  // bir lahza ham bo'sh turmasligi uchun.
  const brandName = kindergartenName || branchName;
  const navItems = navForRole(role);
  // Bildirishnomalar qarzdorlik va to'lovlardan hisoblanadi, ya'ni moliyaviy
  // ma'lumot — shuning uchun qobiliyat ham o'sha.
  const showsFinance = can(role, "finance.view");

  // Bildirishnomalar va yon paneldagi raqamlar — haqiqiy ma'lumotdan
  // hisoblanadi (soxta son ko'rsatilmaydi). Tarbiyachi moliyaviy ma'lumotni
  // ko'rmaydi, shuning uchun unga so'rov ham yuborilmaydi.
  useEffect(() => {
    if (!showsFinance || !branchId) {
      setNotifs([]);
      setCounts({});
      return;
    }
    let cancelled = false;
    Promise.all([
      api
        .dashboard(period.start, period.end, branchId)
        .catch(recoverWith("Moliyaviy xulosa", null)),
      api.listGroups(branchId).catch(recoverWith("Guruhlar", [] as Group[])),
      api.listChildren(branchId).catch(recoverWith("Bolalar", [])),
      api.listStaff(undefined, branchId).catch(recoverWith("Xodimlar", [])),
    ]).then(([dash, groups, children, staff]) => {
      if (cancelled) return;

      // Filial kesimini server bajaradi; bu yerda faqat faollari qoladi.
      const branchGroups = groups.filter((g) => g.is_active);
      setCounts({
        children: children.filter((c) => c.status === "active").length,
        groups: branchGroups.length,
        staff: staff.filter((s) => s.is_active).length,
      });

      const items: NotifItem[] = [];
      const aging = dash?.aging ?? [];
      const late = aging
        .filter((a) => a.label === "aging_31_60" || a.label === "aging_60_plus")
        .reduce((sum, a) => sum + Number(a.total || 0), 0);
      if (late > 0) {
        items.push({
          key: "debt",
          sig: `${branchId}:debt:${late}`,
          href: "/billing",
          title: t.dashboard.over30,
          sub: `${t.dashboard.debt}: ${money(late)}`,
          tone: "neg",
          icon: <IconWallet size={15} />,
        });
      }
      const noTeacher = branchGroups.filter((g) => g.teachers.length === 0);
      for (const g of noTeacher) {
        items.push({
          key: `noteacher-${g.id}`,
          sig: `${branchId}:noteacher:${g.id}`,
          href: "/groups",
          title: `${g.name} — ${t.groups.noTeacher}`,
          sub: t.groups.assignTeacher,
          tone: "warn",
          icon: <IconUser size={15} />,
        });
      }
      setNotifs(items);
    });
    return () => {
      cancelled = true;
    };
  }, [showsFinance, branchId, period.start, period.end, t]);

  /* O'qilmagan savollar — yengil so'rov, shuning uchun davriy yangilanadi.
     Ota-ona botdan yozganda xodim sahifani qayta yuklamasdan ko'radi.
     60 soniya: real vaqt kerak emas, lekin "keyingi kirishgacha ko'rinmaydi"
     ham yaramaydi. Sahifa yashiringanda so'rov yuborilmaydi (fon tabi
     serverga bekorga urilmasin). */
  useEffect(() => {
    if (!showsFinance || !branchId) {
      setUnreadQuestions(0);
      return;
    }
    let cancelled = false;
    const load = (): void => {
      if (document.visibilityState === "hidden") return;
      api
        .unreadMessageCount(branchId)
        .then((r) => {
          if (!cancelled) setUnreadQuestions(r.unread_count);
        })
        .catch(logSecondaryFailure("O'qilmagan savollar"));
    };
    load();
    const timer = window.setInterval(load, 60_000);
    // Xabarlar sahifasida suhbat ochilganda son darhol kamayishi uchun.
    window.addEventListener(MESSAGES_READ_EVENT, load);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener(MESSAGES_READ_EVENT, load);
    };
  }, [showsFinance, branchId]);

  /* O'qilgan bildirishnomalar imzolari. Brauzerda saqlanadi — sahifa
     yangilanganda yana chiqib kelmasligi uchun. localStorage maxfiy rejimda
     istisno tashlashi mumkin, shunda faqat shu sessiya davomida eslanadi. */
  const [readSigs, setReadSigs] = useState<Set<string>>(() => new Set());
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(NOTIF_READ_KEY);
      if (raw) setReadSigs(new Set(JSON.parse(raw) as string[]));
    } catch {
      /* saqlanmagan yoki buzilgan — hammasi o'qilmagan hisoblanadi */
    }
  }, []);

  const quickActions: (CommandItem & { capability: Capability })[] = [
    {
      key: "add-child",
      label: t.children.addChild,
      category: t.common.newLabel,
      capability: "children.manage",
      onSelect: () => router.push("/children?new=1"),
    },
    {
      key: "add-payment",
      label: t.payments.takePayment,
      category: t.common.newLabel,
      capability: "finance.view",
      onSelect: () => router.push("/billing?new=1"),
    },
    {
      key: "add-expense",
      label: t.expenses.addExpense,
      category: t.common.newLabel,
      capability: "finance.view",
      onSelect: () => router.push("/finance/expenses?new=1"),
    },
    {
      key: "add-staff",
      label: t.staff.addStaff,
      category: t.common.newLabel,
      capability: "staff.manage",
      onSelect: () => router.push("/staff?new=1"),
    },
  ];

  // Ctrl+K: sahifalar + amallar (mockupdagidek kategoriya yorlig'i bilan).
  const cmdItems: CommandItem[] = [
    ...navItems.map((item) => ({
      key: `nav-${item.key}`,
      label: t.nav[item.key],
      category: t.nav.sectionGeneral,
      onSelect: () => router.push(item.href),
    })),
    // Har bir tez amal o'z qobiliyati bilan chegaralanadi: menejerga hammasi
    // ochiq, tarbiyachiga esa hech biri — u ochilmaydigan sahifaga tushmasligi
    // uchun.
    ...quickActions
      .filter((action) => can(role, action.capability))
      .map((action): CommandItem => {
        // `capability` faqat filtrlash uchun — CommandItem'ga o'tmaydi.
        const { key, label, category, onSelect } = action;
        return { key, label, category, onSelect };
      }),
    // Chop etish — sof brauzer amali, hech qanday ma'lumotga tegmaydi,
    // shuning uchun rolga bog'lanmaydi.
    {
      key: "print",
      label: t.common.print,
      category: t.common.newLabel,
      onSelect: () => window.print(),
    },
  ];

  // Rol qo'riqchisi: menyusida yo'q sahifaga URL orqali kirilsa, foydalanuvchi
  // o'z bosh sahifasiga qaytariladi. Sahifa kontenti umuman render qilinmaydi —
  // aks holda uning `useEffect`lari backendga so'rov yuborib, 403 xatolar
  // to'plamini va ushlanmagan istisnolarni keltirib chiqaradi.
  const roleKnown = Boolean(role);
  const pageAllowed =
    !roleKnown ||
    (active
      ? navItems.some((i) => i.key === active)
      : requires
        ? can(role, requires)
        : true);

  useEffect(() => {
    if (!roleKnown || pageAllowed) return;
    router.replace(firstHrefForRole(role));
  }, [roleKnown, pageAllowed, role, router]);

  // Ochilayotgan bo'lim sarlavhasi darhol ko'rsatiladi. Sahifa o'z sarlavhasini
  // mount bo'lgandan keyin beradi — usiz yon panelda yangi band yonib turar,
  // topbarda esa hali eski bo'lim nomi qolardi.
  const pendingNav =
    pendingHref !== null
      ? NAV_ITEMS.find((i) => i.href === pendingHref)
      : undefined;
  // Boshqa manzil uchun berilgan (eskirgan) sarlavha ishlatilmaydi — bo'lim
  // almashganda topbarda bir lahza eski nom ko'rinib qolmasligi uchun.
  const meta: PageMeta = pageMeta.path === pathname ? pageMeta : {};
  const pageTitle = pendingNav
    ? t.nav[pendingNav.key]
    : (title ?? meta.title ?? (active ? t.nav[active] : ""));
  const pageSubtitle = pendingNav ? undefined : (subtitle ?? meta.subtitle);

  /* Javobsiz savol eng ustunda turadi — unga tirik odam javob kutyapti. */
  const currentNotifs: NotifItem[] =
    unreadQuestions > 0
      ? [
          {
            key: "messages",
            sig: `${branchId}:messages:${unreadQuestions}`,
            href: "/messages",
            title: t.messaging.newQuestions,
            sub: `${unreadQuestions} ${t.messaging.unreadBadge}`,
            tone: "warn",
            icon: <IconChat size={15} />,
          },
          ...notifs,
        ]
      : notifs;
  // O'qilganlar paneldan yo'qolmaydi — xira ko'rinadi. Son faqat
  // o'qilmaganlarni sanaydi.
  const unreadNotifs = currentNotifs.filter((n) => !readSigs.has(n.sig));

  function markNotifsRead(items: NotifItem[]): void {
    setReadSigs((prev) => {
      // Joriy filialning endi mavjud bo'lmagan eski imzolari tashlanadi —
      // ro'yxat cheksiz o'smasin. Boshqa filiallarniki tegilmaydi.
      const prefix = `${branchId}:`;
      const live = new Set(currentNotifs.map((n) => n.sig));
      const next = new Set(
        [...prev].filter((sig) => !sig.startsWith(prefix) || live.has(sig)),
      );
      for (const n of items) next.add(n.sig);
      try {
        window.localStorage.setItem(NOTIF_READ_KEY, JSON.stringify([...next]));
      } catch {
        /* saqlab bo'lmadi — sessiya davomida baribir yashirin turadi */
      }
      return next;
    });
  }

  function openPeriodPicker(): void {
    modal.open(
      <PeriodForm
        initial={period}
        t={t}
        onApply={(p) => {
          setPeriod(p);
          modal.close();
        }}
      />,
      { title: t.common.period, size: "narrow" },
    );
  }

  function openProfile(): void {
    if (!user) return;
    modal.open(
      <ProfileForm
        user={user}
        t={t}
        onSaved={(updated) => {
          modal.close();
          // Yon paneldagi ism darhol yangilanishi uchun sahifa qayta yuklanadi
          // (user props orqali yuqoridan keladi, shu yerda o'zgartirib bo'lmaydi).
          if (
            updated.full_name !== user.full_name ||
            updated.phone !== user.phone
          ) {
            router.refresh();
          }
        }}
      />,
      { title: t.myProfile, subtitle: displayName, size: "narrow" },
    );
  }

  function openQuickAdd(): void {
    const items: [string, string, ReactNode, string][] = [
      [
        t.children.addChild,
        t.quick.childSub,
        <IconUsers size={19} key="c" />,
        "/children?new=1",
      ],
      [
        t.payments.takePayment,
        t.quick.paymentSub,
        <IconWallet size={19} key="p" />,
        "/billing?new=1",
      ],
      [
        t.expenses.addExpense,
        t.quick.expenseSub,
        <IconTrendingDown size={19} key="e" />,
        "/finance/expenses?new=1",
      ],
      [
        t.staff.addStaff,
        t.quick.staffSub,
        <IconUser size={19} key="s" />,
        "/staff?new=1",
      ],
      [
        t.groups.addGroup,
        t.quick.groupSub,
        <IconBuilding size={19} key="g" />,
        "/groups?new=1",
      ],
      [
        t.messaging.broadcastTitle,
        t.quick.messageSub,
        <IconMessage size={19} key="m" />,
        "/parents",
      ],
    ];
    modal.open(
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map(([label, sub, icon, href]) => (
          <button
            key={href}
            type="button"
            className="btn btn-ghost btn--full"
            style={{
              justifyContent: "flex-start",
              gap: 14,
              padding: "13px 14px",
              height: "auto",
              textAlign: "left",
            }}
            onClick={() => {
              modal.close();
              router.push(href);
            }}
          >
            <span
              style={{ color: "var(--brand)", flex: "none", display: "grid" }}
            >
              {icon}
            </span>
            <span>
              <b style={{ display: "block", fontSize: 14 }}>{label}</b>
              <small
                style={{ fontWeight: 400, color: "var(--ink-3)", fontSize: 12 }}
              >
                {sub}
              </small>
            </span>
          </button>
        ))}
      </div>,
      { title: t.common.whatAdd, size: "narrow" },
    );
  }

  return (
    <AppUIContext.Provider
      value={{
        lang,
        setLang,
        t,
        branches,
        branchId,
        setBranchId,
        period,
        setPeriod,
        setPageMeta,
        role,
        can: canForRole,
      }}
    >
      <div>
        <aside className={`sidebar${sidebarOpen ? " open" : ""}`}>
          <div className="sb__brand">
            <span className="sb__brand-mark">
              {brandName.charAt(0).toUpperCase()}
            </span>
            <span className="sb__name tr">{brandName}</span>
          </div>

          {/* Filial — bog'cha nomi ostida.
              Bir nechta filialga kirish huquqi bo'lsa tanlagich, aks holda
              shunchaki hozirgi filial nomi (bitta filialli bog'chada tanlov
              ma'nosiz, lekin qaysi filialdaligini bilish foydali). */}
          {/* Filiallar ro'yxati API'dan kelguncha `branch` bo'sh bo'ladi va bu
              blok umuman chizilmasdi — kelgach menyu 57px pastga siljirdi
              (CLS). Endi joyi oldindan band qilinadi: yuklanayotganda ham
              o'sha balandlikdagi bo'sh qolip turadi. */}
          {!branch ? (
            <div className="sb__orgbox" aria-hidden="true">
              <div className="sb__org sb__org--skeleton" />
            </div>
          ) : canSwitchBranch ? (
            <div className="pop sb__orgbox" ref={branchRef}>
              <button
                type="button"
                className={`sb__org${branchOpen ? " on" : ""}`}
                aria-haspopup="listbox"
                aria-expanded={branchOpen}
                aria-label={t.common.branch}
                title={branch.name}
                onClick={() => setBranchOpen((v) => !v)}
              >
                <span className="sb__org-ico">
                  <IconBuilding size={15} />
                </span>
                <span className="sb__org-text">
                  <span className="sb__org-label">{t.common.branch}</span>
                  <span className="sb__org-name tr">{branch.name}</span>
                </span>
                <span className="sb__org-caret">
                  <IconChevronDown size={15} />
                </span>
              </button>
              {branchOpen && (
                <div className="pop__panel sb__org-panel" role="listbox">
                  <div className="pop__head">{t.common.branch}</div>
                  {branches.map((b) => (
                    <button
                      key={b.id}
                      type="button"
                      role="option"
                      aria-selected={b.id === branchId}
                      className={`pop__item sb__org-opt${b.id === branchId ? " on" : ""}`}
                      onClick={() => {
                        setBranchId(b.id);
                        setBranchOpen(false);
                      }}
                    >
                      <span className="sb__org-opt-text">
                        <b className="tr">{b.name}</b>
                        {b.address && <span className="tr">{b.address}</span>}
                      </span>
                      {b.id === branchId && <IconCheck size={15} />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="sb__orgbox">
              <div className="sb__org" title={branch.name}>
                <span className="sb__org-ico">
                  <IconBuilding size={15} />
                </span>
                <span className="sb__org-text">
                  <span className="sb__org-label">{t.common.branch}</span>
                  <span className="sb__org-name tr">{branch.name}</span>
                </span>
              </div>
            </div>
          )}

          <nav className="sb__nav">
            {SECTIONS.map((section) => {
              const items = navItems.filter((i) => i.section === section);
              if (items.length === 0) return null;
              const sectionLabel =
                section === "general"
                  ? t.nav.sectionGeneral
                  : section === "kindergarten"
                    ? t.nav.sectionKindergarten
                    : section === "finance"
                      ? t.nav.sectionFinance
                      : t.nav.sectionOther;
              return (
                <div key={section}>
                  <div className="sb__label">{sectionLabel}</div>
                  {items.map((item) => (
                    <Link
                      key={item.key}
                      href={item.href}
                      className={`sb__link${active === item.key ? " active" : ""}`}
                      // Faol band ilgari faqat rang bilan belgilanardi — ekran
                      // o'quvchi qaysi sahifada turganini bilmasdi.
                      aria-current={active === item.key ? "page" : undefined}
                      title={t.nav[item.key]}
                      onClick={() => {
                        setSidebarOpen(false);
                        if (item.href !== pathname) setPendingHref(item.href);
                      }}
                    >
                      {item.icon(17)}
                      <span>{t.nav[item.key]}</span>
                      {counts[item.key] !== undefined && (
                        <span className="sb__count">{counts[item.key]}</span>
                      )}
                    </Link>
                  ))}
                </div>
              );
            })}
          </nav>

          <div className="sb__foot">
            <div className="pop" ref={menuRef} style={{ width: "100%" }}>
              <button
                type="button"
                className="sb__user"
                onClick={() => setMenuOpen((v) => !v)}
              >
                <span className="avatar">{userInitials}</span>
                <div>
                  <b className="tr">{displayName}</b>
                  <span>{roleLabel || "—"}</span>
                </div>
              </button>
              {menuOpen && (
                <div
                  className="pop__panel pop__panel--up"
                  style={{ left: 0, right: 0 }}
                >
                  <button
                    type="button"
                    className="pop__item"
                    onClick={() => {
                      setMenuOpen(false);
                      openProfile();
                    }}
                  >
                    {t.myProfile}
                  </button>
                  <div className="pop__sep" />
                  <div className="pop__head">{t.language}</div>
                  {LANGS.map((l) => (
                    <button
                      key={l}
                      type="button"
                      className={`pop__item${l === lang ? " on" : ""}`}
                      onClick={() => setLang(l)}
                    >
                      {LANG_LABEL[l]}
                    </button>
                  ))}
                  <div className="pop__sep" />
                  <button
                    type="button"
                    className="pop__item"
                    style={{ color: "var(--neg)" }}
                    onClick={logout}
                  >
                    {t.logout}
                  </button>
                </div>
              )}
            </div>
          </div>
        </aside>

        <div className="main">
          <header className="topbar">
            <button
              type="button"
              className="burger"
              onClick={() => setSidebarOpen((v) => !v)}
              aria-label="Menyu"
            >
              <IconMenu size={22} />
            </button>
            <button
              type="button"
              className="btn--icon panel-btn"
              onClick={() => setCollapsed((v) => !v)}
              title={t.collapseMenu}
              aria-label={t.collapseMenu}
              aria-expanded={!collapsed}
            >
              <IconCollapse size={19} />
            </button>
            <div style={{ minWidth: 0 }}>
              <h1 className="tr">{pageTitle}</h1>
              {pageSubtitle && <p className="topbar__sub tr">{pageSubtitle}</p>}
            </div>
            <div className="topbar__right">
              {/* `cmdk-btn` — CSS bu tugmani juda tor ekranda (≤360px)
                  yashiradi: u yerda o'ngdagi boshqaruvlar sahifa sarlavhasiga
                  joy qoldirmaydi. Buyruq paneli klaviatura uchun (Ctrl+K),
                  telefonda esa har bir ro'yxatning o'z qidiruv maydoni bor. */}
              <button
                type="button"
                className="btn--icon cmdk-btn"
                onClick={() => setCmdkOpen(true)}
                title="Ctrl+K"
                aria-label={t.search}
              >
                <IconSearch size={18} />
              </button>
              <button
                type="button"
                className="btn--icon theme-btn"
                onClick={toggleTheme}
                title={t.toggleTheme}
                aria-label={t.toggleTheme}
              >
                {dark ? <IconMoon size={18} /> : <IconSun size={18} />}
              </button>
              {showsFinance && (
                <div className="pop" ref={notifRef}>
                  <button
                    type="button"
                    className="btn--icon bell"
                    onClick={() => setNotifOpen((v) => !v)}
                    title={t.notifications}
                    aria-label={t.notifications}
                  >
                    <IconBell size={18} />
                    {unreadNotifs.length > 0 && (
                      <span className="bell__badge">{unreadNotifs.length}</span>
                    )}
                  </button>
                  {notifOpen && (
                    <div className="pop__panel" style={{ minWidth: 320 }}>
                      <div className="pop__head">{t.notifications}</div>
                      {currentNotifs.length === 0 ? (
                        <p className="panel-empty" style={{ padding: "1rem" }}>
                          {t.noNotifications}
                        </p>
                      ) : (
                        <>
                          {currentNotifs.map((n) => (
                            <button
                              type="button"
                              className={`notif${
                                readSigs.has(n.sig) ? " notif--read" : ""
                              }`}
                              key={n.key}
                              onClick={() => {
                                markNotifsRead([n]);
                                setNotifOpen(false);
                                router.push(n.href);
                              }}
                            >
                              <span
                                className="notif__ico"
                                style={{
                                  background: `var(--${n.tone}-bg)`,
                                  color: `var(--${n.tone})`,
                                }}
                              >
                                {n.icon}
                              </span>
                              <span>
                                <b>{n.title}</b>
                                <small>{n.sub}</small>
                              </span>
                            </button>
                          ))}
                          {unreadNotifs.length > 0 && (
                            <>
                              <div className="pop__sep" />
                              <button
                                type="button"
                                className="pop__item"
                                onClick={() => {
                                  markNotifsRead(unreadNotifs);
                                  setNotifOpen(false);
                                }}
                              >
                                {t.common.markRead}
                              </button>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}
              <button
                type="button"
                className="period"
                onClick={openPeriodPicker}
              >
                <IconCalendar size={15} />
                <span className="period__label">
                  {periodLabel(period.start, period.end, lang)}
                </span>
              </button>
              {showsFinance && (
                <button
                  type="button"
                  className="btn btn-sm new-btn"
                  onClick={openQuickAdd}
                >
                  + <span className="new-txt">{t.common.newLabel}</span>
                </button>
              )}
            </div>
          </header>
          <main className="content">
            {branchesError ? (
              <LoadError
                error={branchesError}
                onRetry={loadBranches}
                title="Filiallar ro'yxatini olishda xatolik"
              />
            ) : showPending ? (
              <PageSkeleton />
            ) : pageAllowed ? (
              /* `key` marshrutga bog'langan — bo'lim almashganda kontent
                 qaytadan chiziladi va yumshoq paydo bo'lish animatsiyasi
                 ishga tushadi. Qobiq esa (yon panel, topbar) joyida qoladi. */
              <div className="content__page" key={pathname}>
                {children}
              </div>
            ) : (
              <div className="boot-screen">KIDSFLOW</div>
            )}
          </main>
        </div>
      </div>

      <div
        className={`scrim${sidebarOpen ? " on" : ""}`}
        style={{ display: sidebarOpen ? "block" : "none" }}
        onClick={() => setSidebarOpen(false)}
      />

      <CommandPalette
        open={cmdkOpen}
        onClose={() => setCmdkOpen(false)}
        items={cmdItems}
        placeholder={t.search}
        emptyLabel={t.common.nothingFound}
      />
    </AppUIContext.Provider>
  );
}
