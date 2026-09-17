"use client";

// Bitta global modal — mockup arxitekturasiga mos (bir vaqtda faqat bitta
// modal ochiq bo'ladi). Sahifalar `useModal().open(...)` orqali chaqiradi.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
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

export function ModalProvider({
  children,
}: {
  children: ReactNode;
}): ReactNode {
  const [entry, setEntry] = useState<{
    content: ReactNode;
    options: ModalOptions;
  } | null>(null);
  const [visible, setVisible] = useState(false);
  const onCloseRef = useRef<(() => void) | undefined>(undefined);
  const boxRef = useRef<HTMLDivElement | null>(null);
  // Modal ochilishidan oldin fokusda turgan element — yopilgach fokus shu
  // yerga qaytadi, aks holda klaviatura bilan ishlayotgan foydalanuvchi
  // sahifa boshiga tashlanadi.
  const restoreRef = useRef<HTMLElement | null>(null);
  // Yopilish animatsiyasining kechiktirilgan tozalash taymeri. `open()` uni
  // bekor qiladi: aks holda "yopib, darhol boshqasini ochish" (masalan bola
  // kartochkasidagi "Tahrirlash") holatida eski taymer 200 ms dan keyin
  // yangi ochilgan oynani o'chirib yuborardi va ekranda hech narsa qolmasdi.
  const closeTimerRef = useRef<number | null>(null);
  const titleId = useId();

  const close = useCallback(() => {
    setVisible(false);
    const cb = onCloseRef.current;
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
    }
    closeTimerRef.current = window.setTimeout(() => {
      closeTimerRef.current = null;
      setEntry(null);
      cb?.();
      restoreRef.current?.focus?.();
      restoreRef.current = null;
    }, 200);
  }, []);

  const open = useCallback((content: ReactNode, options: ModalOptions) => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
      // Oldingi oynaning `onClose`i chaqirilmay qolmasin.
      onCloseRef.current?.();
    }
    onCloseRef.current = options.onClose;
    // Formalar har o'zgarishda `open()`ni qayta chaqiradi (kontent bir marta
    // "suratga olinadi"). Bunda fokus allaqachon oyna ichida bo'ladi —
    // qaytariladigan elementni faqat haqiqiy ochilishda eslab qolamiz.
    const active =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    if (!boxRef.current?.contains(active)) restoreRef.current = active;
    setEntry({ content, options });
    requestAnimationFrame(() => setVisible(true));
  }, []);

  function focusables(): HTMLElement[] {
    const box = boxRef.current;
    if (!box) return [];
    return Array.from(
      box.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((el) => el.offsetParent !== null || el === document.activeElement);
  }

  useEffect(() => {
    if (!visible) return;
    function onKey(e: KeyboardEvent): void {
      if (e.key === "Escape") {
        close();
        return;
      }
      // Fokus tuzog'i: Tab modal ichida aylanadi. Busiz Tab orqa fondagi
      // sahifaga o'tib ketardi va foydalanuvchi ko'rinmaydigan tugmalarni
      // bosishi mumkin edi.
      if (e.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (
        e.shiftKey &&
        (active === first || !boxRef.current?.contains(active))
      ) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [visible, close]);

  // Modal ochiqligida orqa fondagi sahifa skroll bo'lmasin.
  useEffect(() => {
    if (!visible) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [visible]);

  // Ochilganda fokusni modal ichiga olib kiramiz — birinchi matn maydoniga,
  // bo'lmasa birinchi fokuslanadigan elementga.
  useEffect(() => {
    if (!visible || !entry) return;
    const id = window.setTimeout(() => {
      const box = boxRef.current;
      if (!box || box.contains(document.activeElement)) return;
      const field = box.querySelector<HTMLElement>(
        'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])',
      );
      (field ?? focusables()[0])?.focus();
    }, 60);
    return () => window.clearTimeout(id);
  }, [visible, entry]);

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
          <div
            className={`modal${sizeClass}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            ref={boxRef}
          >
            <div className="modal__head">
              <div>
                <h3 id={titleId}>{entry.options.title}</h3>
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
            {entry.options.footer && (
              <div className="modal__foot">{entry.options.footer}</div>
            )}
          </div>
        )}
      </div>
    </ModalContext.Provider>
  );
}
