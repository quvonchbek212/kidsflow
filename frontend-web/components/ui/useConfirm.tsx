"use client";

// Oddiy ha/yo'q tasdiq oynasi (faolsizlantirish/bekor qilish uchun).
// `const ok = await confirm({...})` — promise `true`/`false` bilan yechiladi.

import { useCallback } from "react";
import type { ReactNode } from "react";

import { IconAlert } from "@/components/icons";
import { useModal } from "./ModalProvider";

export interface ConfirmOptions {
  title: string;
  body: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  danger?: boolean;
}

export function useConfirm(): (opts: ConfirmOptions) => Promise<boolean> {
  const modal = useModal();

  return useCallback(
    (opts: ConfirmOptions) =>
      new Promise<boolean>((resolve) => {
        let settled = false;
        function settle(result: boolean): void {
          if (settled) return;
          settled = true;
          resolve(result);
        }
        modal.open(
          <div className="danger-box">
            <IconAlert size={20} />
            <div>
              <p>{opts.body}</p>
            </div>
          </div>,
          {
            title: opts.title,
            size: "narrow",
            onClose: () => settle(false),
            footer: (
              <>
                <span className="spacer" />
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => {
                    settle(false);
                    modal.close();
                  }}
                >
                  {opts.cancelLabel}
                </button>
                <button
                  type="button"
                  className={opts.danger ? "btn btn--danger" : "btn"}
                  onClick={() => {
                    settle(true);
                    modal.close();
                  }}
                >
                  {opts.confirmLabel}
                </button>
              </>
            ),
          },
        );
      }),
    [modal],
  );
}
