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
      <div id="toasts">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast${t.type === "neg" ? " toast--neg" : ""}${t.leaving ? " out" : ""}`}
          >
            {t.type === "neg" ? (
              <IconAlert size={17} />
            ) : (
              <IconCheck size={17} />
            )}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
