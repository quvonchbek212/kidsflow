import type { ReactNode } from "react";

import { IconEmpty } from "@/components/icons";

/**
 * Panel ichidagi bo'sh holat.
 *
 * Ilgari panellar `<div className="panel-empty">` — bitta kulrang qator matn
 * ishlatardi, DataTable esa allaqachon to'liq namunaga (`.state`: ikonka +
 * sarlavha + izoh + harakat) ega edi. Bu komponent o'sha namunani panellarga
 * ham olib keladi, ya'ni yangi uslub o'ylab topilmaydi.
 */
export function EmptyState({
  title,
  hint,
  icon,
  action,
}: {
  title: string;
  hint?: string;
  icon?: ReactNode;
  action?: ReactNode;
}): ReactNode {
  return (
    <div className="state">
      <div className="state__ico">{icon ?? <IconEmpty size={24} />}</div>
      <h4>{title}</h4>
      {hint && <p>{hint}</p>}
      {action}
    </div>
  );
}
