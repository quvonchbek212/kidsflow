"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { MESSAGES_READ_EVENT, useAppUI } from "@/components/AppShell";
import { IconChat } from "@/components/icons";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadError } from "@/components/ui/LoadError";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type MessageThread,
  type ParentMessage,
} from "@/lib/api";
import { initials } from "@/lib/format";

export default function MessagesPage(): ReactNode {
  return <MessagesContent />;
}

/** Vaqtni qisqa ko'rinishda: bugun bo'lsa soat, aks holda sana. */
function shortTime(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const sameDay =
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate();
  return sameDay
    ? d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString();
}

function MessagesContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();
  const toast = useToast();

  useEffect(() => {
    setPageMeta({
      title: t.messaging.threadsTitle,
      subtitle: t.messaging.threadsSubtitle,
    });
  }, [setPageMeta, t]);

  const [threads, setThreads] = useState<MessageThread[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [messages, setMessages] = useState<ParentMessage[]>([]);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);

  // Yangi xabar kelganda yozishma pastiga suriladi.
  const bottomRef = useRef<HTMLDivElement>(null);
  // Davriy yangilash intervali bir marta yaratiladi — `selected` ni closure
  // orqali olsa eskirgan qiymatni ko'rardi.
  const selectedRef = useRef<string | null>(null);
  selectedRef.current = selected;

  const loadThreads = useCallback((): void => {
    if (!branchId) return;
    setLoadError(null);
    api
      .listMessageThreads(branchId)
      .then((rows) => {
        setThreads(rows);
        setReady(true);
      })
      .catch(setLoadError);
  }, [branchId]);

  useEffect(loadThreads, [loadThreads]);

  /* Pochta qutisi ochiq turganda yangi savol o'zi ko'rinishi kerak — aks holda
     xodim sahifani qo'lda yangilamaguncha ota-ona javobsiz qoladi.
     Sahifa yashiringanda so'rov yuborilmaydi. */
  useEffect(() => {
    if (!branchId) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "hidden") return;
      api
        .listMessageThreads(branchId)
        .then(setThreads)
        .catch(() => undefined);
      if (selectedRef.current) {
        api
          .getMessageThread(branchId, selectedRef.current)
          .then(setMessages)
          .catch(() => undefined);
      }
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [branchId]);

  // Suhbat ochilganda backend uni o'qilgan deb belgilaydi, shuning uchun
  // ro'yxatdagi "yangi" sanog'i ham yangilanadi.
  useEffect(() => {
    if (!branchId || !selected) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    api
      .getMessageThread(branchId, selected)
      .then((rows) => {
        if (cancelled) return;
        setMessages(rows);
        // Qo'ng'iroqchadagi o'qilmaganlar soni darhol yangilansin.
        window.dispatchEvent(new Event(MESSAGES_READ_EVENT));
        setThreads((prev) =>
          prev.map((thread) =>
            thread.guardian_user_id === selected
              ? { ...thread, unread_count: 0 }
              : thread,
          ),
        );
      })
      .catch(() => setMessages([]));
    return () => {
      cancelled = true;
    };
  }, [branchId, selected]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  async function submitReply(e: FormEvent): Promise<void> {
    e.preventDefault();
    const text = reply.trim();
    if (!text || !selected || !branchId || sending) return;
    setSending(true);
    try {
      const created = await api.replyToParent(branchId, selected, text);
      setMessages((prev) => [...prev, created]);
      setReply("");
      // Ro'yxatdagi "oxirgi xabar" ham yangilanadi.
      setThreads((prev) =>
        prev.map((thread) =>
          thread.guardian_user_id === selected
            ? {
                ...thread,
                last_message_text: text,
                last_message_at: created.created_at,
              }
            : thread,
        ),
      );
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, {
        type: "neg",
      });
    } finally {
      setSending(false);
    }
  }

  if (loadError) return <LoadError error={loadError} onRetry={loadThreads} />;

  if (ready && threads.length === 0) {
    return (
      <div className="card">
        <EmptyState
          title={t.messaging.threadsEmpty}
          hint={t.messaging.threadsEmptySub}
        />
      </div>
    );
  }

  const active = threads.find((thread) => thread.guardian_user_id === selected);

  return (
    <div className="inbox">
      <aside className="inbox__list card">
        {!ready
          ? Array.from({ length: 4 }).map((_, i) => (
              <div className="inbox__row" key={i}>
                <div
                  className="sk"
                  style={{ width: 36, height: 36, borderRadius: "50%" }}
                />
                <div style={{ flex: 1 }}>
                  <div className="sk sk-line" style={{ width: "60%" }} />
                  <div className="sk sk-line" style={{ width: "85%" }} />
                </div>
              </div>
            ))
          : threads.map((thread) => (
              <button
                type="button"
                key={thread.guardian_user_id}
                className={`inbox__row${
                  thread.guardian_user_id === selected ? " on" : ""
                }`}
                onClick={() => setSelected(thread.guardian_user_id)}
              >
                <span className="avatar">{initials(thread.guardian_name)}</span>
                <span className="inbox__row-body">
                  <span className="inbox__row-top">
                    <b className="tr">{thread.guardian_name}</b>
                    <small>{shortTime(thread.last_message_at)}</small>
                  </span>
                  <small className="tr inbox__preview">
                    {thread.last_message_text}
                  </small>
                  {thread.children.length > 0 && (
                    <small className="tr inbox__children">
                      {thread.children.join(", ")}
                    </small>
                  )}
                </span>
                {thread.unread_count > 0 && (
                  <span className="inbox__unread">{thread.unread_count}</span>
                )}
              </button>
            ))}
      </aside>

      <section className="inbox__thread card">
        {!active ? (
          <div className="state">
            <div className="state__ico">
              <IconChat size={24} />
            </div>
            <h4>{t.messaging.chooseThread}</h4>
          </div>
        ) : (
          <>
            <div className="inbox__head">
              <span className="avatar">{initials(active.guardian_name)}</span>
              <div>
                <b>{active.guardian_name}</b>
                <small>
                  {active.guardian_phone ?? "—"}
                  {active.children.length > 0
                    ? ` · ${active.children.join(", ")}`
                    : ""}
                </small>
              </div>
            </div>

            <div className="inbox__messages">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`bubble bubble--${m.direction === "IN" ? "in" : "out"}`}
                >
                  <p>{m.text}</p>
                  <small>
                    {m.direction === "OUT"
                      ? `${m.staff_name ?? t.messaging.fromStaff} · `
                      : ""}
                    {shortTime(m.created_at)}
                  </small>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            <form className="inbox__reply" onSubmit={submitReply}>
              <input
                className="input"
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                placeholder={t.messaging.replyPlaceholder}
                maxLength={2000}
              />
              <button
                type="submit"
                className="btn"
                disabled={sending || !reply.trim()}
              >
                {t.messaging.replySend}
              </button>
            </form>
          </>
        )}
      </section>
    </div>
  );
}
