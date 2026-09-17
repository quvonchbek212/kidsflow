"use client";

// Global toast xabarlari (`#toasts` konteyner, bitta marta layout'da o'rnatiladi).

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

import { IconAlert, IconCheck } from "@/components/icons";

interface ToastEntry {
  id: number;
  message: string;
  type: "pos" | "neg";
  leaving: boolean;
}

interface ToastOptions {
  type?: "pos" | "neg";
}

interface ToastContextValue {
  show: (message: string, options?: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast ToastProvider ichida ishlatilishi kerak");
  return ctx;
}

let nextId = 1;

export function ToastProvider({
  children,
}: {
  children: ReactNode;
}): ReactNode {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  const show = useCallback((message: string, options: ToastOptions = {}) => {
    const id = nextId++;
    setToasts((prev) => [
      ...prev,
      { id, message, type: options.type ?? "pos", leaving: false },
    ]);
    window.setTimeout(() => {
      setToasts((prev) =>
        prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)),
      );
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 220);
    }, 3200);
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      {/* Ikkita jonli hudud: xatolar darhol ("assertive"), oddiy xabarlar
          esa foydalanuvchi ishini bo'lmasdan ("polite") o'qiladi. Hududlar
          bo'sh bo'lsa ham DOM'da turishi shart — aks holda ichiga qo'shilgan
          matn e'lon qilinmaydi. */}
      <div id="toasts">
        <div className="toasts__region" role="status" aria-live="polite">
          {toasts
            .filter((t) => t.type !== "neg")
            .map((t) => (
              <div key={t.id} className={`toast${t.leaving ? " out" : ""}`}>
                <IconCheck size={17} />
                <span>{t.message}</span>
              </div>
            ))}
        </div>
        <div className="toasts__region" role="alert" aria-live="assertive">
          {toasts
            .filter((t) => t.type === "neg")
            .map((t) => (
              <div
                key={t.id}
                className={`toast toast--neg${t.leaving ? " out" : ""}`}
              >
                <IconAlert size={17} />
                <span>{t.message}</span>
              </div>
            ))}
        </div>
      </div>
    </ToastContext.Provider>
  );
}
