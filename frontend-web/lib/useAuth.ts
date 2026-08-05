"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, type CurrentUser } from "./api";
import { isAuthenticated } from "./auth";

// Sahifani himoyalaydigan hook: token bo'lmasa /login ga yo'naltiradi va
// joriy foydalanuvchini yuklaydi.
export function useAuth(): { user: CurrentUser | null; loading: boolean } {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  return { user, loading };
}
