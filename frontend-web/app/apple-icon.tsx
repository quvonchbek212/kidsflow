import { ImageResponse } from "next/og";

// Safari "bosh ekranga qo'shish" uchun SVG'ni qabul qilmaydi — PNG kerak.
// Shuning uchun icon.svg dan alohida, shu yerda PNG generatsiya qilinadi.
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon(): ImageResponse {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#1668b8",
        }}
      >
        <svg
          width="118"
          height="118"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#fff"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="15.3" cy="4.9" r="2.7" fill="#fff" stroke="none" />
          <path d="M15.3 7.9v5.4" />
          <path d="M15 9.5 20.6 5.4" />
          <path d="M15 10.1 11.3 12.2" />
          <path d="M15.3 13.3 13.3 18.6M15.3 13.3 17.9 18.2" />
          <circle cx="7.5" cy="8.7" r="2.3" fill="#fff" stroke="none" />
          <path d="M7.5 11.2v4.4" />
          <path d="M7.7 12.3 2.6 9.6" />
          <path d="M7.9 12.3 11.3 12.2" />
          <path d="M7.5 15.6 5.8 20.1M7.5 15.6 9.8 19.7" />
        </svg>
      </div>
    ),
    size,
  );
}
