// Toza chiziqli (stroke) SVG ikonlar — currentColor'dan rang oladi (emoji o'rniga).

import type { ReactNode } from "react";

type P = { size?: number };

function base(children: ReactNode, size = 22): ReactNode {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

export const IconUsers = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </>,
    size,
  );

export const IconBuilding = ({ size }: P): ReactNode =>
  base(
    <>
      <rect x="4" y="3" width="16" height="18" rx="1.5" />
      <path d="M9 8h.01M15 8h.01M9 12h.01M15 12h.01M9 16h6" />
    </>,
    size,
  );

export const IconGrid = ({ size }: P): ReactNode =>
  base(
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>,
    size,
  );

export const IconReceipt = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M5 3v18l2-1.5L9 21l2-1.5L13 21l2-1.5L17 21l2-1.5V3l-2 1.5L15 3l-2 1.5L11 3 9 4.5 7 3 5 4.5" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </>,
    size,
  );

export const IconWallet = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M3 7a2 2 0 0 1 2-2h13a1 1 0 0 1 1 1v3" />
      <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2H6a3 3 0 0 1-3-3Z" />
      <path d="M16 13h.01" />
    </>,
    size,
  );

export const IconAlert = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M10.3 3.6 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.6a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </>,
    size,
  );

export const IconTrendingDown = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M22 17 13.5 8.5 8.5 13.5 2 7" />
      <path d="M16 17h6v-6" />
    </>,
    size,
  );

export const IconGift = ({ size }: P): ReactNode =>
  base(
    <>
      <rect x="3" y="8" width="18" height="4" rx="1" />
      <path d="M12 8v13M5 12v7a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-7" />
      <path d="M12 8S10.5 4 8 4a2 2 0 1 0 0 4M12 8s1.5-4 4-4a2 2 0 1 1 0 4" />
    </>,
    size,
  );

export const IconSearch = ({ size }: P): ReactNode =>
  base(
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </>,
    size,
  );

export const IconSun = ({ size }: P): ReactNode =>
  base(
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>,
    size,
  );

export const IconMoon = ({ size }: P): ReactNode =>
  base(<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" />, size);

export const IconBell = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </>,
    size,
  );

export const IconCollapse = ({ size }: P): ReactNode =>
  base(<path d="m15 18-6-6 6-6" />, size);

export const IconShield = ({ size }: P): ReactNode =>
  base(<path d="M12 3 4 6v6c0 5 3.5 8.5 8 9 4.5-.5 8-4 8-9V6Z" />, size);

export const IconChevronDown = ({ size }: P): ReactNode =>
  base(<path d="m6 9 6 6 6-6" />, size);

export const IconUser = ({ size }: P): ReactNode =>
  base(
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" />
    </>,
    size,
  );

export const IconLogout = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5" />
      <path d="M21 12H9" />
    </>,
    size,
  );

export const IconCalendar = ({ size }: P): ReactNode =>
  base(
    <>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </>,
    size,
  );

export const IconX = ({ size }: P): ReactNode =>
  base(<path d="M18 6 6 18M6 6l12 12" />, size);

export const IconPlus = ({ size }: P): ReactNode =>
  base(<path d="M12 5v14M5 12h14" />, size);

export const IconCheck = ({ size }: P): ReactNode => base(<path d="M20 6 9 17l-5-5" />, size);

export const IconChevronLeft = ({ size }: P): ReactNode =>
  base(<path d="m15 18-6-6 6-6" />, size);

export const IconChevronRight = ({ size }: P): ReactNode =>
  base(<path d="m9 18 6-6-6-6" />, size);

export const IconMenu = ({ size }: P): ReactNode =>
  base(<path d="M3 6h18M3 12h18M3 18h18" />, size);

export const IconEdit = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </>,
    size,
  );

export const IconTrash = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6" />
      <path d="M10 11v6M14 11v6" />
    </>,
    size,
  );

export const IconArrowUpRight = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </>,
    size,
  );

export const IconMessage = ({ size }: P): ReactNode =>
  base(
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />,
    size,
  );

export const IconSettings = ({ size }: P): ReactNode =>
  base(
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </>,
    size,
  );

export const IconUpload = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M17 8l-5-5-5 5" />
      <path d="M12 3v12" />
    </>,
    size,
  );

// Bo'sh holat uchun (mockupdagi kalendar-quti ikonkasi).
export const IconEmpty = ({ size }: P): ReactNode =>
  base(
    <>
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M16 3v4M8 3v4M3 12h18" />
    </>,
    size,
  );

// Yuklab olish (hisobot ro'yxatidagi strelka).
export const IconDownload = ({ size }: P): ReactNode =>
  base(
    <>
      <path d="M12 4v12M7 11l5 5 5-5M4 20h16" />
    </>,
    size,
  );
