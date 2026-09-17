"use client";

import type { ReactNode } from "react";

import { LoadError } from "@/components/ui/LoadError";

/**
 * Foydalanuvchi hali yuklanmaganda sahifa o'rniga ko'rsatiladigan ekran.
 *
 * Yuklanayotganda — brend ekrani (avvalgidek). Nosozlikda esa sababi va
 * "Qayta urinish" tugmasi: server o'chgan paytda foydalanuvchi login
 * sahifasiga uloqtirilib, sababini bilmay qolmasligi kerak.
 */
export function authFallback({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error: unknown;
  retry: () => void;
}): ReactNode {
  if (error && !loading) {
    return (
      <div className="boot-screen boot-screen--error">
        <LoadError
          error={error}
          onRetry={retry}
          title="Tizimga ulanib bo'lmadi"
        />
      </div>
    );
  }
  return <div className="boot-screen">KIDSFLOW</div>;
}
