"use client";

// Ilova qobig'i (yon panel + topbar) shu yerda, ildiz layout ichida turadi.
//
// Ilgari har bir sahifa o'zi `<AppShell>` ni chizardi. Next.js sahifani
// almashtirganda butun daraxtni yechib tashlaydi, ya'ni har bo'lim ochilganda
// yon panel va topbar yo'q qilinib qaytadan quriladi: ekran bir necha kadr
// "KIDSFLOW" yuklanish ekraniga tushib qimirlar, `/auth/me`, `/branches` va
// `/settings` esa qayta so'ralardi. Layout esa marshrutlar orasida saqlanadi —
// endi faqat kontent almashadi.

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AppShell, type NavKey } from "@/components/AppShell";
import { useAuth } from "@/lib/useAuth";
import type { Capability } from "@/lib/permissions";

/** Qobiqsiz sahifalar: kirish, parol tiklash va 404. */
const BARE = ["/login", "/forgot-password", "/reset-password"];

/** Marshrut → yon paneldagi faol band. */
const ACTIVE: Record<string, NavKey> = {
  "/dashboard": "dashboard",
  "/children": "children",
  "/groups": "groups",
  "/attendance": "attendance",
  "/daily-reports": "dailyReports",
  "/staff": "staff",
  "/billing": "payments",
  "/finance/expenses": "expenses",
  "/finance/reports": "reports",
  "/parents": "parents",
  "/messages": "inbox",
  "/settings": "settings",
};

/** Menyuda bandi yo'q, lekin huquq talab qiladigan marshrutlar. */
const REQUIRES: Record<string, Capability> = {
  "/food/meals": "finance.view",
  "/food/products": "finance.view",
  "/food/report": "finance.view",
};

export function AppChrome({ children }: { children: ReactNode }): ReactNode {
  const pathname = usePathname() ?? "";
  const known = pathname in ACTIVE || pathname in REQUIRES;

  // Kirish sahifalari va noma'lum manzillar (404) qobiqsiz chiziladi.
  if (BARE.includes(pathname) || !known) return <>{children}</>;

  return (
    <AuthedChrome
      active={ACTIVE[pathname]}
      requires={REQUIRES[pathname]}
      // Marshrut o'zgarganda AppShell qayta mount bo'lmasligi kerak —
      // `key` berilmaydi, faqat proplar yangilanadi.
    >
      {children}
    </AuthedChrome>
  );
}

function AuthedChrome({
  active,
  requires,
  children,
}: {
  active?: NavKey;
  requires?: Capability;
  children: ReactNode;
}): ReactNode {
  const { user, loading, fallback } = useAuth();
  if (loading || !user) return fallback;
  return (
    <AppShell user={user} active={active} requires={requires}>
      {children}
    </AppShell>
  );
}
