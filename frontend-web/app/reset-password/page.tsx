"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent, type ReactNode } from "react";

import { api, ApiError } from "@/lib/api";
import type { Lang } from "@/lib/landing-content";

const LANGS: Lang[] = ["uz", "ru", "en"];

const T: Record<
  Lang,
  {
    title: string;
    subtitle: string;
    back: string;
    password: string;
    confirm: string;
    submit: string;
    submitting: string;
    success: string;
    mismatch: string;
    missingToken: string;
  }
> = {
  uz: {
    title: "Yangi parol",
    subtitle: "Hisobingiz uchun yangi parol o'rnating",
    back: "Kirishga qaytish",
    password: "Yangi parol",
    confirm: "Yangi parolni takrorlang",
    submit: "Parolni saqlash",
    submitting: "Saqlanmoqda...",
    success: "Parol muvaffaqiyatli o'zgartirildi. Endi tizimga kirishingiz mumkin.",
    mismatch: "Parollar mos kelmadi.",
    missingToken: "Havola yaroqsiz — token topilmadi.",
  },
  ru: {
    title: "Новый пароль",
    subtitle: "Установите новый пароль для аккаунта",
    back: "Назад ко входу",
    password: "Новый пароль",
    confirm: "Повторите новый пароль",
    submit: "Сохранить пароль",
    submitting: "Сохранение...",
    success: "Пароль успешно изменён. Теперь вы можете войти.",
    mismatch: "Пароли не совпадают.",
    missingToken: "Ссылка недействительна — токен не найден.",
  },
  en: {
    title: "New password",
    subtitle: "Set a new password for your account",
    back: "Back to sign in",
    password: "New password",
    confirm: "Repeat new password",
    submit: "Save password",
    submitting: "Saving...",
    success: "Password changed successfully. You can now sign in.",
    mismatch: "Passwords do not match.",
    missingToken: "Invalid link — token not found.",
  },
};

export default function ResetPasswordPage(): ReactNode {
  return (
    <Suspense fallback={<div className="boot-screen">KIDSFLOW</div>}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm(): ReactNode {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [lang, setLang] = useState<Lang>("uz");
  const t = T[lang];

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError(t.mismatch);
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => router.replace("/login"), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Xatolik yuz berdi.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-brandside">
        <div className="auth-mark">
          <span className="auth-dot">B</span> KIDSFLOW
        </div>
        <p className="auth-pitch">{t.subtitle}</p>
      </div>
      <div className="auth-formside">
        <div className="auth-form">
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
            <Link href="/login" className="btn-ghost btn btn-sm">
              ← {t.back}
            </Link>
            <div className="segmented" style={{ width: "auto" }}>
              {LANGS.map((l) => (
                <button
                  type="button"
                  key={l}
                  className={l === lang ? "on" : ""}
                  onClick={() => setLang(l)}
                >
                  {l.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <h2>{t.title}</h2>
          <p>{t.subtitle}</p>

          {!token ? (
            <p className="error">{t.missingToken}</p>
          ) : success ? (
            <div className="info-box">{t.success}</div>
          ) : (
            <form onSubmit={onSubmit}>
              <div className="field">
                <label>{t.password}</label>
                <input
                  className="input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
              </div>
              <div className="field">
                <label>{t.confirm}</label>
                <input
                  className="input"
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
              </div>
              {error && <p className="error">{error}</p>}
              <button className="btn btn--full" type="submit" disabled={loading} style={{ marginTop: 8 }}>
                {loading ? t.submitting : t.submit}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
