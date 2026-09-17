"use client";

// Ildiz layout'ining o'zi yiqilganda ishlaydi — bu holda `app/error.tsx` ham
// chizilmaydi, chunki u layout ichida turadi. Shu sababli bu fayl o'z <html>
// va <body> teglarini beradi va hech qanday umumiy uslubga tayanmaydi
// (globals.css ham yuklanmagan bo'lishi mumkin).

import { useEffect, type ReactNode } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): ReactNode {
  useEffect(() => {
    console.error("Ildiz layoutida xatolik:", error);
  }, [error]);

  return (
    <html lang="uz">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          padding: "1.5rem",
          background: "#f6f7f9",
          color: "#1a1d26",
          fontFamily:
            "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        }}
      >
        <div style={{ maxWidth: "30rem", textAlign: "center" }}>
          <h1
            style={{
              fontSize: "1.35rem",
              fontWeight: 700,
              margin: "0 0 0.75rem",
            }}
          >
            Ilovani yuklab bo&apos;lmadi
          </h1>
          <p style={{ lineHeight: 1.6, color: "#4a5060", margin: 0 }}>
            Kutilmagan xatolik yuz berdi. Sahifani yangilab ko&apos;ring; xato
            takrorlansa qo&apos;llab-quvvatlashga murojaat qiling.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              marginTop: "1.25rem",
              padding: "0.65rem 1.1rem",
              borderRadius: "10px",
              border: "none",
              background: "#1668b8",
              color: "#fff",
              fontSize: "0.95rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Qayta urinish
          </button>
          {error.digest && (
            <p
              style={{
                marginTop: "1rem",
                fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
                fontSize: "0.78rem",
                color: "#757c8c",
                wordBreak: "break-all",
              }}
            >
              So&apos;rov raqami: {error.digest}
            </p>
          )}
        </div>
      </body>
    </html>
  );
}
