"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { useModal } from "@/components/ui/ModalProvider";
import { APP_I18N, type AppStrings } from "@/lib/app-i18n";
import { ApiError, api, type Branch, type CurrentUser, type Group } from "@/lib/api";
import { initials, isoDate, money, monthRange, periodLabel } from "@/lib/format";
import type { Lang } from "@/lib/landing-content";

interface NotifItem {
  key: string;
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
  | "settings";

type Section = "general" | "kindergarten" | "finance" | "other";

interface NavItem {
  key: NavKey;
  href: string;
  section: Section;
  icon: (size?: number) => ReactNode;
}

// Tartib mockupdagi bilan bir xil: Umumiy → Bog'cha → Moliya → Boshqa.
const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", href: "/dashboard", section: "general", icon: (s) => <IconGrid size={s} /> },
  {
    key: "reports",
    href: "/finance/reports",
    section: "general",
    icon: (s) => <IconReceipt size={s} />,
  },
  { key: "children", href: "/children", section: "kindergarten", icon: (s) => <IconUsers size={s} /> },
  { key: "groups", href: "/groups", section: "kindergarten", icon: (s) => <IconBuilding size={s} /> },
  {
    key: "attendance",
    href: "/attendance",
    section: "kindergarten",
    icon: (s) => <IconCalendar size={s} />,
  },
  {
    key: "dailyReports",
    href: "/daily-reports",
    section: "kindergarten",
    icon: (s) => <IconEdit size={s} />,
  },
  { key: "staff", href: "/staff", section: "kindergarten", icon: (s) => <IconUser size={s} /> },
  { key: "payments", href: "/billing", section: "finance", icon: (s) => <IconWallet size={s} /> },
  {
    key: "expenses",
    href: "/finance/expenses",
    section: "finance",
    icon: (s) => <IconTrendingDown size={s} />,
  },
  { key: "parents", href: "/parents", section: "other", icon: (s) => <IconMessage size={s} /> },
  { key: "settings", href: "/settings", section: "other", icon: (s) => <IconSettings size={s} /> },
];

const SECTIONS: Section[] = ["general", "kindergarten", "finance", "other"];
// Tarbiyachi davomat belgilaydi va kunlik hisobot yozadi — bu ikkisi uning
// kundalik ishi (4.3, 4.4-bo'lim). Qolgan bo'limlar unga ko'rinmaydi.
const TEACHER_KEYS: NavKey[] = ["attendance", "dailyReports"];

function navForRole(role: string): NavItem[] {
  if (role === "TEACHER") return NAV_ITEMS.filter((i) => TEACHER_KEYS.includes(i.key));
  return NAV_ITEMS;
}

/** Rol uchun birinchi ochiladigan sahifa (menyudagi eng yuqorisi). */
function firstHrefForRole(role: string): string {
  return navForRole(role)[0]?.href ?? "/attendance";
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
      <div className="field">
        <label>{t.common.fullName}</label>
        <input
          className="input"
          required
          maxLength={255}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
      </div>
      <div className="field">
        <label>{t.common.phone}</label>
        <input
          className="input"
          placeholder="+998 90 123 45 67"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
      </div>

      {error && <p className="error">{error}</p>}
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
      <div className="field">
        <label>{t.common.quickPick}</label>
        <div className="segmented">
          {quickItems.map(([label, kind]) => (
            <button
              key={kind}
              type="button"
              className={active(kind) ? "on" : ""}
              onClick={() => quick(kind)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="form-grid">
        <div className="field">
          <label>{t.common.from}</label>
          <input
            className="input"
            type="date"
            value={draft.start}
            onChange={(e) => setDraft((d) => ({ ...d, start: e.target.value }))}
          />
        </div>
        <div className="field">
          <label>{t.common.to}</label>
          <input
            className="input"
            type="date"
            value={draft.end}
            onChange={(e) => setDraft((d) => ({ ...d, end: e.target.value }))}
          />
        </div>
      </div>
      <button type="button" className="btn btn--full" onClick={() => onApply(draft)}>
        {t.common.apply}
      </button>
    </>
  );
}

export function AppShell({
  user,
  active,
  title,
  subtitle,
  children,
}: {
  user: CurrentUser | null;
  active?: NavKey;
  title?: string;
  subtitle?: string;
  children: ReactNode;
}): ReactNode {
  const router = useRouter();
  const modal = useModal();
  const [lang, setLangState] = useState<Lang>("uz");
  const [dark, setDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const [notifs, setNotifs] = useState<NotifItem[]>([]);
  const [counts, setCounts] = useState<Partial<Record<NavKey, number>>>({});
  const [pageMeta, setPageMetaState] = useState<PageMeta>({});
  const menuRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchId, setBranchIdState] = useState("");
  const [period, setPeriodState] = useState<Period>(() => monthRange());

  useEffect(() => {
    api.listBranches().then(setBranches).catch(() => {});
    const saved = window.localStorage.getItem("kidsflow_branch_id");
    if (saved) setBranchIdState(saved);
  }, []);

  function setBranchId(id: string): void {
    setBranchIdState(id);
    window.localStorage.setItem("kidsflow_branch_id", id);
  }

  const setPeriod = useCallback((p: Period) => setPeriodState(p), []);

  // Bir xil qiymat qayta yozilib, cheksiz render tsikliga tushmasligi uchun
  // faqat haqiqatan o'zgarganda holat yangilanadi.
  const setPageMeta = useCallback((meta: PageMeta) => {
    setPageMetaState((prev) =>
      prev.title === meta.title && prev.subtitle === meta.subtitle ? prev : meta,
    );
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent): void {
      if (menuOpen && menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
      if (notifOpen && notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen, notifOpen]);

  // Sidebar yig'ilgan holati `body` klassiga yoziladi (CSS shunga tayanadi).
  useEffect(() => {
    document.body.classList.toggle("collapsed", collapsed);
    return () => document.body.classList.remove("collapsed");
  }, [collapsed]);

  useEffect(() => {
    const savedLang = window.localStorage.getItem("kidsflow_lang") as Lang | null;
    if (savedLang) setLangState(savedLang);
    const savedTheme = window.localStorage.getItem("kidsflow_theme");
    if (savedTheme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
      setDark(true);
    }
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

  function toggleTheme(): void {
    const next = !dark;
    setDark(next);
    if (next) document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    window.localStorage.setItem("kidsflow_theme", next ? "dark" : "light");
  }

  async function logout(): Promise<void> {
    await api.logout();
    router.replace("/login");
  }

  const t = APP_I18N[lang];
  const role = user?.roles?.[0]?.role ?? "";
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
  const navItems = navForRole(role);
  const isOwnerOrManager = role === "OWNER" || role === "MANAGER";

  // Bildirishnomalar va yon paneldagi raqamlar — haqiqiy ma'lumotdan
  // hisoblanadi (soxta son ko'rsatilmaydi). Faqat OWNER/MANAGER uchun,
  // chunki tarbiyachi moliyaviy ma'lumotni ko'rmaydi.
  useEffect(() => {
    if (!isOwnerOrManager || !branchId) {
      setNotifs([]);
      setCounts({});
      return;
    }
    let cancelled = false;
    Promise.all([
      api.dashboard(period.start, period.end).catch(() => null),
      api.listGroups().catch(() => [] as Group[]),
      api.listChildren().catch(() => []),
      api.listStaff().catch(() => []),
    ]).then(([dash, groups, children, staff]) => {
      if (cancelled) return;

      const branchGroups = groups.filter((g) => g.branch_id === branchId && g.is_active);
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
  }, [isOwnerOrManager, branchId, period.start, period.end, t]);

  // Ctrl+K: sahifalar + amallar (mockupdagidek kategoriya yorlig'i bilan).
  const cmdItems: CommandItem[] = [
    ...navItems.map((item) => ({
      key: `nav-${item.key}`,
      label: t.nav[item.key],
      category: t.nav.sectionGeneral,
      onSelect: () => router.push(item.href),
    })),
    ...(isOwnerOrManager
      ? [
          {
            key: "add-child",
            label: t.children.addChild,
            category: t.common.newLabel,
            onSelect: () => router.push("/children?new=1"),
          },
          {
            key: "add-payment",
            label: t.payments.takePayment,
            category: t.common.newLabel,
            onSelect: () => router.push("/billing?new=1"),
          },
          {
            key: "add-expense",
            label: t.expenses.addExpense,
            category: t.common.newLabel,
            onSelect: () => router.push("/finance/expenses?new=1"),
          },
          {
            key: "add-staff",
            label: t.staff.addStaff,
            category: t.common.newLabel,
            onSelect: () => router.push("/staff?new=1"),
          },
          {
            key: "print",
            label: t.common.print,
            category: t.common.newLabel,
            onSelect: () => window.print(),
          },
        ]
      : []),
  ];

  // Rol qo'riqchisi: menyusida yo'q sahifaga URL orqali kirilsa, foydalanuvchi
  // o'z bosh sahifasiga qaytariladi. Sahifa kontenti umuman render qilinmaydi —
  // aks holda uning `useEffect`lari backendga so'rov yuborib, 403 xatolar
  // to'plamini va ushlanmagan istisnolarni keltirib chiqaradi.
  const roleKnown = Boolean(role);
  const pageAllowed = !active || !roleKnown || navItems.some((i) => i.key === active);

  useEffect(() => {
    if (!roleKnown || pageAllowed) return;
    router.replace(firstHrefForRole(role));
  }, [roleKnown, pageAllowed, role, router]);

  const pageTitle = title ?? pageMeta.title ?? (active ? t.nav[active] : "");
  const pageSubtitle = subtitle ?? pageMeta.subtitle;

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
          if (updated.full_name !== user.full_name || updated.phone !== user.phone) {
            router.refresh();
          }
        }}
      />,
      { title: t.myProfile, subtitle: displayName, size: "narrow" },
    );
  }

  function openQuickAdd(): void {
    const items: [string, string, ReactNode, string][] = [
      [t.children.addChild, t.quick.childSub, <IconUsers size={19} key="c" />, "/children?new=1"],
      [t.payments.takePayment, t.quick.paymentSub, <IconWallet size={19} key="p" />, "/billing?new=1"],
      [
        t.expenses.addExpense,
        t.quick.expenseSub,
        <IconTrendingDown size={19} key="e" />,
        "/finance/expenses?new=1",
      ],
      [t.staff.addStaff, t.quick.staffSub, <IconUser size={19} key="s" />, "/staff?new=1"],
      [t.groups.addGroup, t.quick.groupSub, <IconBuilding size={19} key="g" />, "/groups?new=1"],
      [t.messaging.broadcastTitle, t.quick.messageSub, <IconMessage size={19} key="m" />, "/parents"],
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
            <span style={{ color: "var(--brand)", flex: "none", display: "grid" }}>{icon}</span>
            <span>
              <b style={{ display: "block", fontSize: 14 }}>{label}</b>
              <small style={{ fontWeight: 400, color: "var(--ink-3)", fontSize: 12 }}>{sub}</small>
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
      }}
    >
      <div>
        <aside className={`sidebar${sidebarOpen ? " open" : ""}`}>
          <div className="sb__brand">
            <span className="sb__brand-mark">{branchName.charAt(0).toUpperCase()}</span>
            <span className="sb__name tr">
              {branchName}
              <small className="tr">{roleLabel}</small>
            </span>
          </div>

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
                      title={t.nav[item.key]}
                      onClick={() => setSidebarOpen(false)}
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
              <button type="button" className="sb__user" onClick={() => setMenuOpen((v) => !v)}>
                <span className="avatar">{userInitials}</span>
                <div>
                  <b className="tr">{displayName}</b>
                  <span>{roleLabel || "—"}</span>
                </div>
              </button>
              {menuOpen && (
                <div className="pop__panel pop__panel--up" style={{ left: 0, right: 0 }}>
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
                  {/* Filial almashtirish mockupda yo'q, lekin ko'p filialli
                      hisoblar uchun kerak — yon panel ko'rinishini buzmasligi
                      uchun shu menyuga joylashtirilgan. */}
                  {canSwitchBranch && (
                    <>
                      <div className="pop__sep" />
                      <div className="pop__head">{t.common.branch}</div>
                      {branches.map((b) => (
                        <button
                          key={b.id}
                          type="button"
                          className={`pop__item${b.id === branchId ? " on" : ""}`}
                          onClick={() => {
                            setBranchId(b.id);
                            setMenuOpen(false);
                          }}
                        >
                          {b.name}
                        </button>
                      ))}
                    </>
                  )}
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
              <button
                type="button"
                className="btn--icon"
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
              {isOwnerOrManager && (
                <div className="pop" ref={notifRef}>
                  <button
                    type="button"
                    className="btn--icon bell"
                    onClick={() => setNotifOpen((v) => !v)}
                    title={t.notifications}
                    aria-label={t.notifications}
                  >
                    <IconBell size={18} />
                    {notifs.length > 0 && <span className="bell__badge">{notifs.length}</span>}
                  </button>
                  {notifOpen && (
                    <div className="pop__panel" style={{ minWidth: 320 }}>
                      <div className="pop__head">{t.notifications}</div>
                      {notifs.length === 0 ? (
                        <p className="panel-empty" style={{ padding: "1rem" }}>
                          {t.noNotifications}
                        </p>
                      ) : (
                        <>
                          {notifs.map((n) => (
                            <button
                              type="button"
                              className="notif"
                              key={n.key}
                              onClick={() => setNotifOpen(false)}
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
                          <div className="pop__sep" />
                          <button
                            type="button"
                            className="pop__item"
                            onClick={() => setNotifOpen(false)}
                          >
                            {t.common.markRead}
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}
              <button type="button" className="period" onClick={openPeriodPicker}>
                <IconCalendar size={15} />
                <span className="period__label">{periodLabel(period.start, period.end, lang)}</span>
              </button>
              {isOwnerOrManager && (
                <button type="button" className="btn btn-sm new-btn" onClick={openQuickAdd}>
                  + <span className="new-txt">{t.common.newLabel}</span>
                </button>
              )}
            </div>
          </header>
          <main className="content">
            {pageAllowed ? children : <div className="boot-screen">KIDSFLOW</div>}
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
