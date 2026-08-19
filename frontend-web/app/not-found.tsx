import type { ReactNode } from "react";

export default function NotFound(): ReactNode {
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
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
        </span>
        <h1 className="fault__title">Bunday sahifa yo&apos;q</h1>
        <p className="fault__text">
          Havola eskirgan yoki manzil noto&apos;g&apos;ri kiritilgan
          bo&apos;lishi mumkin.
        </p>
        <div className="fault__actions">
          <a className="btn" href="/dashboard">
            Bosh sahifa
          </a>
        </div>
      </div>
    </div>
  );
}
