// Token saqlash (client-side). MVP uchun localStorage; production'da httpOnly
// cookie'ga o'tkazish tavsiya etiladi.

const ACCESS_KEY = "kidsflow_access_token";
const REFRESH_KEY = "kidsflow_refresh_token";

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: AuthTokens): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, tokens.accessToken);
  window.localStorage.setItem(REFRESH_KEY, tokens.refreshToken);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

// Access token muddati tugagan bo'lsa ham refresh token bilan sessiyani tiklash
// mumkin — shuning uchun ikkalasidan biri yetarli. Haqiqiy tekshiruvni `/auth/me`
// bajaradi (kerak bo'lsa api klienti tokenni yangilab, so'rovni qaytaradi).
export function isAuthenticated(): boolean {
  return getToken() !== null || getRefreshToken() !== null;
}
