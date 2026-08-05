"use client";

// Bitta global modal — mockup arxitekturasiga mos (bir vaqtda faqat bitta
// modal ochiq bo'ladi). Sahifalar `useModal().open(...)` orqali chaqiradi.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { IconX } from "@/components/icons";

export type ModalSize = "narrow" | "default" | "wide";

export interface ModalOptions {
  title: ReactNode;
  subtitle?: ReactNode;
  size?: ModalSize;
  footer?: ReactNode;
  /** Modal yopilganda chaqiriladi (masalan formani tozalash uchun). */
  onClose?: () => void;
}

interface ModalContextValue {
  open: (content: ReactNode, options: ModalOptions) => void;
  close: () => void;
}

const ModalContext = createContext<ModalContextValue | null>(null);

export function useModal(): ModalContextValue {
  const ctx = useContext(ModalContext);
  if (!ctx) throw new Error("useModal ModalProvider ichida ishlatilishi kerak");
  return ctx;
}

export function ModalProvider({ children }: { children: ReactNode }): ReactNode {
  const [entry, setEntry] = useState<{ content: ReactNode; options: ModalOptions } | null>(
    null,
  );
  const [visible, setVisible] = useState(false);
  const onCloseRef = useRef<(() => void) | undefined>(undefined);

  const close = useCallback(() => {
    setVisible(false);
    const cb = onCloseRef.current;
    window.setTimeout(() => {
      setEntry(null);
      cb?.();
    }, 200);
  }, []);

  const open = useCallback((content: ReactNode, options: ModalOptions) => {
    onCloseRef.current = options.onClose;
    setEntry({ content, options });
    requestAnimationFrame(() => setVisible(true));
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent): void {
      if (e.key === "Escape" && visible) close();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [visible, close]);

  const sizeClass =
    entry?.options.size === "wide"
      ? " modal--wide"
      : entry?.options.size === "narrow"
        ? " modal--narrow"
        : "";

  return (
    <ModalContext.Provider value={{ open, close }}>
      {children}
      <div
        className={`modal-scrim${visible ? " on" : ""}`}
        onClick={(e) => {
          if (e.target === e.currentTarget) close();
        }}
        aria-hidden={!visible}
      >
        {entry && (
          <div className={`modal${sizeClass}`} role="dialog" aria-modal="true">
            <div className="modal__head">
              <div>
                <h3>{entry.options.title}</h3>
                {entry.options.subtitle && <p>{entry.options.subtitle}</p>}
              </div>
              <button
                className="btn--icon modal__x"
                onClick={close}
                type="button"
                aria-label="Yopish"
              >
                <IconX size={19} />
              </button>
            </div>
            <div className="modal__body">{entry.content}</div>
            {entry.options.footer && <div className="modal__foot">{entry.options.footer}</div>}
          </div>
        )}
      </div>
    </ModalContext.Provider>
  );
}
