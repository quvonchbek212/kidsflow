import type { ReactNode } from "react";

/**
 * Bo'lim ochilayotganda kontent o'rnida turadigan skelet.
 *
 * Sahifalar `force-dynamic` (CSP nonce sababli), ya'ni bosilgandan keyin
 * serverdan javob kutiladi. Busiz shu vaqt davomida ekranda hali eski bo'lim
 * turar va "bosdim, hech narsa bo'lmadi" degan taassurot berardi. Skelet
 * Suspense chegarasi sifatida darhol chiziladi — bosish shu zahoti seziladi.
 */
export function PageSkeleton(): ReactNode {
  return (
    <div className="card" aria-hidden="true">
      <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
        <div className="sk sk-line" style={{ width: "32%" }} />
        <div className="sk sk-block" style={{ height: 96, marginTop: 18 }} />
        <div className="sk sk-block" style={{ height: 220, marginTop: 14 }} />
      </div>
    </div>
  );
}
