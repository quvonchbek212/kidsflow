"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";

import { IconKids, IconEye, IconEyeOff } from "@/components/icons";
import { AuthTopbar } from "@/components/ui/AuthTopbar";
import { api, ApiError } from "@/lib/api";
import { homeHrefFor } from "@/lib/permissions";
import { primaryRole } from "@/lib/roles";
import { setTokens } from "@/lib/auth";
import type { Lang } from "@/lib/lang";

const T: Record<
  Lang,
  {
    theme: string;
    language: string;
    signIn: string;
    signInSub: string;
    login: string;
    password: string;
    showPassword: string;
    hidePassword: string;
    forgot: string;
    submit: string;
    submitting: string;
    error: string;
  }
> = {
  uz: {
    theme: "Mavzuni almashtirish",
    language: "Til",
    signIn: "Tizimga kirish",
    signInSub: "Hisobingizga kiring",
    login: "Login",
    password: "Parol",
    showPassword: "Parolni ko'rsatish",
    hidePassword: "Parolni yashirish",
    forgot: "Parolni unutdingizmi?",
    submit: "Kirish",
    submitting: "Kirilmoqda...",
    error: "Login yoki parol noto'g'ri.",
  },
  ru: {
    theme: "Сменить тему",
    language: "Язык",
    signIn: "Вход в систему",
    signInSub: "Войдите в свой аккаунт",
    login: "Логин",
    password: "Пароль",
    showPassword: "Показать пароль",
    hidePassword: "Скрыть пароль",
    forgot: "Забыли пароль?",
    submit: "Войти",
    submitting: "Вход...",
    error: "Неверный логин или пароль.",
  },
  en: {
    theme: "Toggle theme",
    language: "Language",
    signIn: "Sign in",
    signInSub: "Access your account",
    login: "Login",
    password: "Password",
    showPassword: "Show password",
    hidePassword: "Hide password",
    forgot: "Forgot password?",
    submit: "Sign in",
    submitting: "Signing in...",
    error: "Invalid login or password.",
  },
};

// Backend noto'g'ri login/parol uchun doim shu matnni qaytaradi. Uni tanlangan
// tilga o'giramiz — qolgan xabarlar (hisob bloklangan, hisob faol emas) esa
// o'zgarishsiz ko'rsatiladi, chunki ular boshqa-boshqa holatni bildiradi va
// foydalanuvchi nima bo'lganini bilishi kerak.
const BACKEND_INVALID_CREDENTIALS = "Login yoki parol noto'g'ri.";

function messageFor(err: unknown, t: (typeof T)[Lang]): string {
  if (!(err instanceof ApiError)) return t.error;
  if (err.status === 401 && err.message === BACKEND_INVALID_CREDENTIALS) {
    return t.error;
  }
  return err.message;
}

export default function LoginPage(): ReactNode {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("uz");
  const t = T[lang];

  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
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
      // Har rolning boshlang'ich sahifasi bitta joyda belgilangan
      // (`lib/permissions.ts`) — yon panel ham o'sha manbadan o'qiydi.
      const role = primaryRole(me.roles);
      router.replace(homeHrefFor(role) ?? "/dashboard");
    } catch (err) {
      setError(messageFor(err, t));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <AuthTopbar
        lang={lang}
        setLang={setLang}
        themeLabel={t.theme}
        languageLabel={t.language}
      />
      <div className="auth-card">
        <div className="auth-mark">
          <span className="auth-dot">
            <IconKids size={32} />
          </span>
          <span className="auth-wordmark">KIDSFLOW</span>
        </div>
        <div className="auth-form">
          <h2>{t.signIn}</h2>
          <p>{t.signInSub}</p>
          <form onSubmit={onSubmit}>
            <label className="field">
              <span className="field__label">{t.login}</span>
              <input
                className="input"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                placeholder="Quvonchbek"
                autoComplete="username"
                required
              />
            </label>
            <div className="field">
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <label htmlFor="login-password">{t.password}</label>
                <Link
                  href="/forgot-password"
                  style={{ fontSize: 12.5, fontWeight: 600 }}
                >
                  {t.forgot}
                </Link>
              </div>
              <div className="password-field">
                <input
                  id="login-password"
                  className="input"
                  type={passwordVisible ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setPasswordVisible((v) => !v)}
                  aria-label={passwordVisible ? t.hidePassword : t.showPassword}
                  title={passwordVisible ? t.hidePassword : t.showPassword}
                  aria-pressed={passwordVisible}
                >
                  {passwordVisible ? (
                    <IconEyeOff size={18} />
                  ) : (
                    <IconEye size={18} />
                  )}
                </button>
              </div>
            </div>
            {error && <p className="error" role="alert">{error}</p>}
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
