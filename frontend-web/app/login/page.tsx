"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";

import { api, ApiError } from "@/lib/api";
import { primaryRole } from "@/lib/roles";
import { setTokens } from "@/lib/auth";
import type { Lang } from "@/lib/landing-content";

const LANGS: Lang[] = ["uz", "ru", "en"];

const T: Record<
  Lang,
  {
    pitch: string;
    signIn: string;
    signInSub: string;
    login: string;
    password: string;
    forgot: string;
    submit: string;
    submitting: string;
    error: string;
    back: string;
  }
> = {
  uz: {
    pitch: "Bolalar, to'lovlar va foyda — bitta ekranda.",
    signIn: "Tizimga kirish",
    signInSub: "Hisobingizga kiring",
    login: "Login",
    password: "Parol",
    forgot: "Parolni unutdingizmi?",
    submit: "Kirish",
    submitting: "Kirilmoqda...",
    error: "Login yoki parol noto'g'ri.",
    back: "Bosh sahifaga",
  },
  ru: {
    pitch: "Дети, оплаты и прибыль — на одном экране.",
    signIn: "Вход в систему",
    signInSub: "Войдите в свой аккаунт",
    login: "Логин",
    password: "Пароль",
    forgot: "Забыли пароль?",
    submit: "Войти",
    submitting: "Вход...",
    error: "Неверный логин или пароль.",
    back: "На главную",
  },
  en: {
    pitch: "Children, payments and profit — on one screen.",
    signIn: "Sign in",
    signInSub: "Access your account",
    login: "Login",
    password: "Password",
    forgot: "Forgot password?",
    submit: "Sign in",
    submitting: "Signing in...",
    error: "Invalid login or password.",
    back: "To homepage",
  },
};

export default function LoginPage(): ReactNode {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("uz");
  const t = T[lang];

  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const tokens = await api.login(login, password);
      setTokens({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      });
      const me = await api.me();
      const role = primaryRole(me.roles);
      router.replace(role === "TEACHER" ? "/attendance" : "/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.error);
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
        <p className="auth-pitch">{t.pitch}</p>
        <div className="auth-meta">
          <Link href="/" style={{ color: "#fff" }}>
            ← {t.back}
          </Link>
        </div>
      </div>
      <div className="auth-formside">
        <div className="auth-lang">
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
        <div className="auth-form">
          <h2>{t.signIn}</h2>
          <p>{t.signInSub}</p>
          <form onSubmit={onSubmit}>
            <div className="field">
              <label>{t.login}</label>
              <input
                className="input"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                placeholder="Quvonchbek"
                autoComplete="username"
                required
              />
            </div>
            <div className="field">
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <label>{t.password}</label>
                <Link
                  href="/forgot-password"
                  style={{ fontSize: 12.5, fontWeight: 600 }}
                >
                  {t.forgot}
                </Link>
              </div>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && <p className="error">{error}</p>}
            <button
              className="btn btn--full"
              type="submit"
              disabled={loading}
              style={{ marginTop: 8 }}
            >
              {loading ? t.submitting : t.submit}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
