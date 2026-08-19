"use client";

// Marshrut segmentidagi kutilmagan xatoni ushlaydi. Busiz render vaqtidagi
// istalgan istisno butun sahifani oq ekranga aylantirardi — tiklanish yo'lisiz.

import { useEffect, type ReactNode } from "react";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): ReactNode {
  useEffect(() => {
    // Konsolga to'liq xato — brauzerda ochib ko'rish uchun. Foydalanuvchi
    // faqat tushunarli xabar va `digest` raqamini ko'radi.
    console.error("Sahifada xatolik:", error);
  }, [error]);

  return (
    <div className="fault">
      <div className="fault__box">
        <span className="fault__mark" aria-hidden="true">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
            <path d="M12 9v4" />
            <path d="M12 17h.01" />
          </svg>
        </span>
        <h1 className="fault__title">Sahifani ko&apos;rsatib bo&apos;lmadi</h1>
        <p className="fault__text">
          Kutilmagan xatolik yuz berdi. Ma&apos;lumotlaringiz saqlanib qolgan —
          qayta urinib ko&apos;ring yoki bosh sahifaga qayting.
        </p>
        <div className="fault__actions">
          <button type="button" className="btn" onClick={reset}>
            Qayta urinish
          </button>
          <a className="btn btn-ghost" href="/dashboard">
            Bosh sahifa
          </a>
        </div>
        {error.digest && (
          <p className="fault__ref">
            So&apos;rov raqami: {error.digest}
            <br />
            Qo&apos;llab-quvvatlashga murojaat qilsangiz shu raqamni ayting.
          </p>
        )}
      </div>
    </div>
  );
}
