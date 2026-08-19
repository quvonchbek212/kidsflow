import type { ReactNode } from "react";

import { ApiError } from "@/lib/api";

/**
 * Sahifaning asosiy ma'lumoti yuklanmaganda ko'rsatiladigan holat.
 *
 * Ilgari bunday xatolar `.catch(() => {})` bilan yutilar va foydalanuvchi
 * bo'sh jadval ko'rardi — bu "tizim ishlamayapti" emas, "ma'lumotlarim
 * yo'qoldi" degan taassurot berardi. Endi sabab aytiladi va qayta urinish
 * imkoni beriladi.
 */
export function LoadError({
  error,
  onRetry,
  title = "Ma'lumotni yuklab bo'lmadi",
}: {
  error: unknown;
  onRetry: () => void;
  title?: string;
}): ReactNode {
  return (
    <div className="card load-error">
      <div className="load-error__body">
        <h3 className="load-error__title">{title}</h3>
        <p className="load-error__text">{describeError(error)}</p>
      </div>
      <button type="button" className="btn btn-sm" onClick={onRetry}>
        Qayta urinish
      </button>
    </div>
  );
}

/** Xatoni foydalanuvchi tushunadigan jumlaga aylantiradi. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return "Bu bo'limga kirish huquqingiz yo'q.";
    if (error.status === 404) return "So'ralgan ma'lumot topilmadi.";
    if (error.status >= 500)
      return "Server javob bermayapti. Birozdan so'ng qayta urinib ko'ring.";
    return error.message;
  }
  // `fetch` tarmoq uzilganda TypeError beradi — eng ko'p uchraydigan holat.
  if (error instanceof TypeError)
    return "Internetga ulanib bo'lmadi. Aloqani tekshiring.";
  return "Kutilmagan xatolik yuz berdi.";
}

/**
 * Ikkilamchi (boyituvchi) so'rovlar uchun: sahifa ularsiz ham ishlaydi,
 * shuning uchun ekranni to'sib qo'ymaymiz — lekin konsolga yozamiz, aks holda
 * nosozlikni keyin topib bo'lmaydi.
 */
export function logSecondaryFailure(what: string): (error: unknown) => void {
  return (error: unknown) => {
    console.warn(`[kidsflow] ${what} yuklanmadi:`, error);
  };
}

/**
 * `logSecondaryFailure` ning qiymat qaytaradigan varianti — `.catch()` dan
 * keyin ish davom etishi kerak bo'lgan joylar uchun (masalan har bir guruh
 * bo'yicha aylanma so'rovda bitta guruh yiqilsa, qolganlari ishlayversin).
 */
export function recoverWith<T>(
  what: string,
  fallback: T,
): (error: unknown) => T {
  return (error: unknown) => {
    console.warn(`[kidsflow] ${what} yuklanmadi:`, error);
    return fallback;
  };
}
