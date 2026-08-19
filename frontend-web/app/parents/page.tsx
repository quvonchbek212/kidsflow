"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { IconMessage, IconUsers } from "@/components/icons";
import { LoadError, logSecondaryFailure } from "@/components/ui/LoadError";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type BroadcastAudience,
  type Group,
  type KindergartenSettings,
  type MessagingStats,
  type ParentRow,
} from "@/lib/api";
import { initials } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function ParentsPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="parents">
      <ParentsContent />
    </AppShell>
  );
}

const TOGGLE_KEYS = [
  "CHILD_CHECKED_IN",
  "CHILD_SICK",
  "PAYMENT_REMINDER",
  "DEBT_WARNING",
  "BIRTHDAY_GREETING",
] as const;

function ParentsContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.messaging.title, subtitle: t.messaging.subtitle });
  }, [setPageMeta, t]);
  const toast = useToast();

  const [parents, setParents] = useState<ParentRow[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [stats, setStats] = useState<MessagingStats | null>(null);
  const [settings, setSettings] = useState<KindergartenSettings | null>(null);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);

  // Dashboarddagi "Qarzdorlarga eslatma" tugmasi shu yerga `?audience=debtors`
  // bilan olib keladi — auditoriya darhol tanlangan bo'ladi.
  const [audience, setAudience] = useState<BroadcastAudience>(() => {
    if (typeof window === "undefined") return "all";
    const q = new URLSearchParams(window.location.search).get("audience");
    return q === "debtors" || q === "group" ? (q as BroadcastAudience) : "all";
  });
  const [groupId, setGroupId] = useState("");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [inviting, setInviting] = useState("");
  const modal = useModal();

  function load(): void {
    // Filial aniqlanmaguncha kutamiz — server filtri shu parametrga tayanadi.
    if (!branchId) return;
    setLoadError(null);
    // Ota-onalar ro'yxati — sahifaning asosiy mazmuni; u kelmasa xato
    // ko'rsatiladi. Qolganlari sahifani boyitadi, ularsiz ham ishlaydi.
    Promise.all([api.listParents(branchId), api.listGroups(branchId)])
      .then(([parentRows, groupRows]) => {
        setParents(parentRows);
        setGroups(groupRows);
      })
      .catch(setLoadError);
    api
      .getSettings()
      .then(setSettings)
      .catch(logSecondaryFailure("Sozlamalar"));
    api
      .messagingStats(branchId)
      .then(setStats)
      .catch(logSecondaryFailure("Xabar statistikasi"))
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId]);

  function toggleLabel(key: (typeof TOGGLE_KEYS)[number]): string {
    switch (key) {
      case "CHILD_CHECKED_IN":
        return t.messaging.notifChildCheckedIn;
      case "CHILD_SICK":
        return t.messaging.notifChildSick;
      case "PAYMENT_REMINDER":
        return t.messaging.notifPaymentReminder;
      case "DEBT_WARNING":
        return t.messaging.notifDebtWarning;
      case "BIRTHDAY_GREETING":
        return t.messaging.notifBirthdayGreeting;
    }
  }

  // Har bir turning qachon yuborilishi — mockupdagi izoh qatori.
  function toggleHint(key: (typeof TOGGLE_KEYS)[number]): string {
    switch (key) {
      case "CHILD_CHECKED_IN":
        return t.messaging.hintCheckedIn;
      case "CHILD_SICK":
        return t.messaging.hintSick;
      case "PAYMENT_REMINDER":
        return t.messaging.hintPaymentReminder;
      case "DEBT_WARNING":
        return t.messaging.hintDebtWarning;
      case "BIRTHDAY_GREETING":
        return t.messaging.hintBirthday;
    }
  }

  async function onToggle(key: string, checked: boolean): Promise<void> {
    const updated = await api.updateSettings({
      notification_toggles: { [key]: checked },
    });
    setSettings(updated);
  }

  // Ota-onani botga ulash uchun bir martalik kod. Kod ekranda ko'rsatiladi —
  // menejer uni og'zaki yoki qo'lda ota-onaga beradi (7-bo'lim).
  async function onInvite(parent: ParentRow): Promise<void> {
    if (inviting) return;
    setInviting(parent.id);
    try {
      const invitation = await api.createInvitation(parent.id);
      const expires = new Date(invitation.expires_at).toLocaleString();
      modal.open(
        <div>
          <p className="hint" style={{ marginTop: 0 }}>
            {t.messaging.inviteSteps}
          </p>
          <div className="invite-code">
            <code>{invitation.code}</code>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                void navigator.clipboard
                  ?.writeText(invitation.code)
                  .then(() => toast.show(t.messaging.inviteCopied))
                  .catch(logSecondaryFailure("Nusxa olish"));
              }}
            >
              {t.messaging.inviteCopy}
            </button>
          </div>
          <p className="hint">
            {t.messaging.inviteExpires}: {expires}
          </p>
        </div>,
        {
          title: t.messaging.inviteTitle,
          subtitle: `${parent.full_name} — ${t.messaging.inviteSubtitle}`,
          size: "narrow",
        },
      );
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle);
    } finally {
      setInviting("");
    }
  }

  async function onBroadcast(e: FormEvent): Promise<void> {
    e.preventDefault();
    setSending(true);
    setError("");
    try {
      const result = await api.broadcastMessage({
        branch_id: branchId,
        audience,
        group_id: audience === "group" ? groupId : undefined,
        text,
      });
      toast.show(`${result.queued_count} ${t.messaging.sent}`);
      setText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.common.errTitle);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {/* KPI — mockupdagi 3 ustunli qator. "O'qilish darajasi" ataylab yo'q:
          backendda o'qilganlik kuzatuvi yo'q, soxta raqam ko'rsatilmaydi. */}
      <div className="grid g-3 mb-4">
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.messaging.connectedFamilies}</span>
            <IconMessage size={18} />
          </div>
          <div className="kpi__value">
            {ready ? (stats?.connected_families ?? 0) : "—"}
          </div>
        </div>
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.messaging.sentThisMonth}</span>
          </div>
          <div className="kpi__value">
            {ready ? (stats?.sent_this_month ?? 0) : "—"}
            <span className="kpi__unit">{t.messaging.messagesUnit}</span>
          </div>
        </div>
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.messaging.parentsListTitle}</span>
            <IconUsers size={18} />
          </div>
          <div className="kpi__value">{ready ? parents.length : "—"}</div>
        </div>
      </div>

      {/* Mockupdagidek ikki ustun: chapda avtomatik bildirishnomalar,
          o'ngda ommaviy xabar formasi. */}
      <div className="grid g-2 mb-4">
        <div className="card">
          <div className="card__head">
            <div>
              <h3>{t.messaging.autoNotifications}</h3>
              <p>{t.messaging.autoNotificationsSub}</p>
            </div>
          </div>
          <div className="card__body">
            {TOGGLE_KEYS.map((key) => {
              const on = settings?.notification_toggles?.[key] ?? true;
              return (
                <div className="switch-row" key={key}>
                  <div>
                    <b>{toggleLabel(key)}</b>
                    <small>{toggleHint(key)}</small>
                  </div>
                  <button
                    type="button"
                    className={`switch${on ? " on" : ""}`}
                    aria-pressed={on}
                    aria-label={toggleLabel(key)}
                    onClick={() => onToggle(key, !on)}
                  />
                </div>
              );
            })}
          </div>
        </div>

        <div className="card">
          <div className="card__head">
            <div>
              <h3>{t.messaging.broadcastTitle}</h3>
              <p>{t.messaging.broadcastSub}</p>
            </div>
          </div>
          <div className="card__body">
            <form onSubmit={onBroadcast}>
              <div className="field">
                <label>{t.messaging.audience}</label>
                <select
                  className="input"
                  value={audience}
                  onChange={(e) =>
                    setAudience(e.target.value as BroadcastAudience)
                  }
                >
                  <option value="all">{t.messaging.audienceAll}</option>
                  <option value="group">{t.messaging.audienceGroup}</option>
                  <option value="debtors">{t.messaging.audienceDebtors}</option>
                </select>
              </div>
              {audience === "group" && (
                <div className="field">
                  <label>{t.pages.chooseGroup}</label>
                  <select
                    className="input"
                    value={groupId}
                    onChange={(e) => setGroupId(e.target.value)}
                  >
                    <option value="">—</option>
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="field">
                <label>{t.messaging.messageText}</label>
                <textarea
                  className="input"
                  rows={5}
                  required
                  placeholder={t.messaging.messagePlaceholder}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </div>
              {error && <p className="error">{error}</p>}
              <button
                className="btn btn--full"
                type="submit"
                disabled={sending || (audience === "group" && !groupId)}
              >
                {sending ? t.common.saving : t.messaging.send}
              </button>
              <p className="hint">{t.messaging.sendHint}</p>
            </form>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card__head">
          <div>
            <h3>{t.messaging.parentsListTitle}</h3>
          </div>
        </div>
        {loadError ? (
          <LoadError error={loadError} onRetry={load} />
        ) : !ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : parents.length === 0 ? (
          <div className="panel-empty">{t.common.empty}</div>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.common.name}</th>
                  <th>{t.common.phone}</th>
                  <th>{t.common.email}</th>
                  <th>{t.children.guardianSection}</th>
                  <th className="r">Telegram</th>
                </tr>
              </thead>
              <tbody>
                {parents.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div className="cell-name">
                        <span className="avatar">{initials(p.full_name)}</span>
                        <b className="tr">{p.full_name}</b>
                      </div>
                    </td>
                    <td
                      className="num"
                      style={{ fontSize: 13, color: "var(--ink-2)" }}
                    >
                      {p.phone ?? "—"}
                    </td>
                    <td style={{ color: "var(--ink-2)" }}>{p.email ?? "—"}</td>
                    <td style={{ color: "var(--ink-2)" }}>
                      {p.children_names.join(", ") || "—"}
                    </td>
                    <td className="r">
                      {p.telegram_linked ? (
                        <span className="badge badge--pos">
                          {t.common.active}
                        </span>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-ghost btn--sm"
                          disabled={inviting === p.id}
                          onClick={() => void onInvite(p)}
                        >
                          {inviting === p.id
                            ? t.common.saving
                            : t.messaging.inviteGet}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
