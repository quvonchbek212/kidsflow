"use client";

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";

import { api, ApiError } from "@/lib/api";
import type { Lang } from "@/lib/landing-content";

const LANGS: Lang[] = ["uz", "ru", "en"];

const T: Record<
  Lang,
  {
    title: string;
    subtitle: string;
    back: string;
    email: string;
    submit: string;
    submitting: string;
    sent: string;
  }
> = {
  uz: {
    title: "Parolni tiklash",
    subtitle: "Ro'yxatdan o'tgan emailingizni kiriting",
    back: "Kirishga qaytish",
    email: "Email",
    submit: "Havola yuborish",
    submitting: "Yuborilmoqda...",
    sent: "Agar bu email tizimda mavjud bo'lsa, tiklash havolasi yuborildi. Pochtangizni tekshiring.",
  },
  ru: {
    title: "Восстановление пароля",
    subtitle: "Введите зарегистрированный email",
    back: "Назад ко входу",
    email: "Email",
    submit: "Отправить ссылку",
    submitting: "Отправка...",
    sent: "Если такой email зарегистрирован, ссылка для восстановления отправлена. Проверьте почту.",
  },
  en: {
    title: "Reset password",
    subtitle: "Enter your registered email",
    back: "Back to sign in",
    email: "Email",
    submit: "Send reset link",
    submitting: "Sending...",
    sent: "If that email is registered, a reset link has been sent. Check your inbox.",
  },
};

export default function ForgotPasswordPage(): ReactNode {
  const [lang, setLang] = useState<Lang>("uz");
  const t = T[lang];

  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.forgotPassword(email);
      setSent(true);
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

          {sent ? (
            <div className="info-box">{t.sent}</div>
          ) : (
            <form onSubmit={onSubmit}>
              <div className="field">
                <label>{t.email}</label>
                <input
                  className="input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
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
