"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { api } from "@/lib/api";

export function Nav({ userName }: { userName?: string }): ReactNode {
  const router = useRouter();

  async function logout(): Promise<void> {
    await api.logout();
    router.replace("/login");
  }

  return (
    <nav className="nav">
      <span className="brand">KIDSFLOW</span>
      <Link href="/dashboard">Dashboard</Link>
      <Link href="/children">Bolalar</Link>
      <Link href="/billing">To&apos;lovlar</Link>
      <span className="spacer" />
      {userName && <span className="muted">{userName}</span>}
      <button className="btn btn-ghost" onClick={logout}>
        Chiqish
      </button>
    </nav>
  );
}
