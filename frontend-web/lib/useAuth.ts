"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { ApiError, api, type CurrentUser } from "./api";
import { isAuthenticated } from "./auth";
import { authFallback } from "@/components/ui/AuthFallback";

/**
 * Sahifani himoyalaydigan hook: token bo'lmasa /login ga yo'naltiradi va
 * joriy foydalanuvchini yuklaydi.
 *
 * Muhim farq: har qanday nosozlik "kirish rad etildi" degani emas. Ilgari
 * `api.me()` dagi ixtiyoriy xato /login ga uloqtirardi — server o'chgan yoki
 * internet uzilgan paytda foydalanuvchi go'yo paroli xato bo'lgandek login
 * sahifasini ko'rar, qayta kirishga urinar va yana yiqilardi. Endi faqat
 * haqiqiy autentifikatsiya xatosi (401/403) chiqarib yuboradi; tarmoq yoki
 * server nosozligida sabab va "Qayta urinish" tugmasi ko'rsatiladi.
 */
export function useAuth(): {
  user: CurrentUser | null;
  loading: boolean;
  /** `user` bo'lmaganda sahifa shuni qaytaradi: yuklanish ekrani yoki xato. */
  fallback: ReactNode;
} {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .me()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const authFailure =
          err instanceof ApiError && (err.status === 401 || err.status === 403);
        if (authFailure) router.replace("/login");
        else setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return {
    user,
    loading,
    fallback: user ? null : authFallback({ loading, error, retry }),
  };
}
