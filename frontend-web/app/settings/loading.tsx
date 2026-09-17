import type { ReactNode } from "react";

import { PageSkeleton } from "@/components/ui/PageSkeleton";

/** Bo'lim ochilguncha ko'rinadigan skelet (Next.js Suspense chegarasi). */
export default function Loading(): ReactNode {
  return <PageSkeleton />;
}
