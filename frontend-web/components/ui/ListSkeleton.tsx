import type { ReactNode } from "react";

/**
 * Ro'yxat yuklanayotgandagi qolip.
 *
 * Nega bitta chiziq emas, aynan qatorlar: yuklanish holati past bo'lsa,
 * ma'lumot kelganda blok birdan o'sib, ostidagi hamma narsani pastga surib
 * yuboradi (CLS). Qatorlar soni odatdagi ro'yxatga yaqin bo'lgani uchun
 * balandlik deyarli o'zgarmaydi va ekran "sakramaydi".
 */
export function ListSkeleton({
  rows = 6,
  avatar = true,
}: {
  rows?: number;
  avatar?: boolean;
}): ReactNode {
  return (
    <div aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div className="sk-row" key={i}>
          {avatar && (
            <div
              className="sk"
              style={{ width: 34, height: 34, borderRadius: "50%" }}
            />
          )}
          <div style={{ flex: 1 }}>
            <div
              className="sk sk-line"
              style={{ width: `${38 - (i % 3) * 6}%` }}
            />
            <div
              className="sk sk-line"
              style={{ width: `${24 - (i % 2) * 5}%` }}
            />
          </div>
          <div className="sk sk-line" style={{ width: 90 }} />
        </div>
      ))}
    </div>
  );
}
