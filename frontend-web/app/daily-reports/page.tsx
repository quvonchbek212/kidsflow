"use client";

// Kunlik hisobot (4.4-bo'lim): tarbiyachi guruhdagi har bir bola uchun hisobot
// yozadi → qoralama saqlanadi → e'lon qilinadi. E'lon qilingach hisobot
// o'zgarmas bo'ladi va outbox orqali ota-onaga Telegram xabari yuboriladi.

import { useCallback, useEffect, useState, type ReactNode } from "react";

import { useAppUI } from "@/components/AppShell";
import { useModal } from "@/components/ui/ModalProvider";
import { LoadError } from "@/components/ui/LoadError";
import { useToast } from "@/components/ui/ToastProvider";
import { useConfirm } from "@/components/ui/useConfirm";
import { EmptyState } from "@/components/ui/EmptyState";
import { GroupPicker, groupPickerLabels } from "@/components/ui/GroupPicker";
import {
  ApiError,
  api,
  type DailyReport,
  type DailyReportInput,
  type DailyReportRosterRow,
  type Group,
  type MealStatus,
  type Mood,
} from "@/lib/api";
import { initials, isoDate } from "@/lib/format";

export default function DailyReportsPage(): ReactNode {
  return <DailyReportsContent />;
}

function DailyReportsContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();
  const toast = useToast();
  const modal = useModal();
  const confirm = useConfirm();

  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [date, setDate] = useState(isoDate(new Date()));
  const [roster, setRoster] = useState<DailyReportRosterRow[]>([]);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    setPageMeta({
      title: t.dailyReports.title,
      subtitle: t.dailyReports.subtitle,
    });
  }, [setPageMeta, t]);

  // Guruhlar tanlangan filial bo'yicha — filial almashsa tanlov ham qayta quriladi.
  useEffect(() => {
    if (!branchId) return;
    api
      .listGroups(branchId)
      .then((list) => {
        setGroups(list);
        setGroupId(list.length > 0 ? list[0].id : "");
      })
      .catch(setLoadError);
  }, [branchId]);

  // Qaytgan funksiya — eskirgan javobni bekor qilish. Guruh tez almashtirilsa,
  // oldingi guruhning kechikkan javobi yangisining ustiga yozilmasin.
  const load = useCallback((): (() => void) | undefined => {
    if (!groupId || !date) {
      setRoster([]);
      setReady(true);
      return undefined;
    }
    let cancelled = false;
    setReady(false);
    setLoadError(null);
    api
      .dailyReportRoster(groupId, date)
      .then((rows) => {
        if (!cancelled) setRoster(rows);
      })
      .catch((err) => {
        if (cancelled) return;
        setRoster([]);
        setLoadError(err);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [groupId, date]);

  useEffect(load, [load]);

  const MEALS: { value: MealStatus; label: string }[] = [
    { value: "ATE_WELL", label: t.dailyReports.mealAteWell },
    { value: "ATE_SOME", label: t.dailyReports.mealAteSome },
    { value: "REFUSED", label: t.dailyReports.mealRefused },
  ];
  const MOODS: { value: Mood; label: string }[] = [
    { value: "HAPPY", label: t.dailyReports.moodHappy },
    { value: "CALM", label: t.dailyReports.moodCalm },
    { value: "TIRED", label: t.dailyReports.moodTired },
    { value: "SAD", label: t.dailyReports.moodSad },
    { value: "SICK", label: t.dailyReports.moodSick },
  ];

  // Forma modal ichida yashaydi va ModalProvider bitta `ReactNode` saqlaydi,
  // shuning uchun holat local o'zgaruvchilarda turadi va har o'zgarishda
  // qaytadan render qilinadi (children sahifasidagi forma bilan bir xil usul).
  function openForm(row: DailyReportRosterRow): void {
    const existing = row.report;
    const readOnly = existing?.is_published ?? false;

    let meal: MealStatus | "" = existing?.meal_status ?? "";
    let mood: Mood | "" = existing?.mood ?? "";
    let nap = existing?.nap_minutes != null ? String(existing.nap_minutes) : "";
    let activities = existing?.activities_text ?? "";
    let note = existing?.teacher_note ?? "";
    let summary = existing?.final_summary ?? "";
    let saving = false;
    let error = "";

    function payload(): DailyReportInput {
      return {
        meal_status: meal || null,
        mood: mood || null,
        nap_minutes: nap.trim() === "" ? null : Number(nap),
        activities_text: activities.trim() || null,
        teacher_note: note.trim() || null,
        final_summary: summary.trim() || null,
      };
    }

    async function save(): Promise<void> {
      saving = true;
      error = "";
      render();
      try {
        if (existing) {
          await api.updateDailyReport(existing.id, payload());
        } else {
          await api.createDailyReport(row.child_id, date, payload());
        }
        modal.close();
        toast.show(t.dailyReports.savedDraft);
        load();
      } catch (err) {
        error = err instanceof ApiError ? err.message : t.common.errTitle;
        saving = false;
        render();
      }
    }

    function render(): void {
      modal.open(
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!readOnly && !saving) void save();
          }}
        >
          {readOnly && <p className="hint">{t.dailyReports.publishedLocked}</p>}

          {/* Chip qatori — bu yerda `<label>` ishlamaydi (u bitta boshqaruv
              elementiga bog'lanadi), shuning uchun guruh sifatida e'lon
              qilinadi va tugmalar bosilgan holatini bildiradi. */}
          <div className="field" role="group" aria-labelledby="dr-meal-label">
            <span className="field__label" id="dr-meal-label">
              {t.dailyReports.meal}
            </span>
            <div className="toolbar">
              {MEALS.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  disabled={readOnly}
                  aria-pressed={meal === m.value}
                  className={`chip${meal === m.value ? " on" : ""}`}
                  onClick={() => {
                    meal = meal === m.value ? "" : m.value;
                    render();
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="field" role="group" aria-labelledby="dr-mood-label">
            <span className="field__label" id="dr-mood-label">
              {t.dailyReports.mood}
            </span>
            <div className="toolbar">
              {MOODS.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  disabled={readOnly}
                  aria-pressed={mood === m.value}
                  className={`chip${mood === m.value ? " on" : ""}`}
                  onClick={() => {
                    mood = mood === m.value ? "" : m.value;
                    render();
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <label className="field">
            <span className="field__label">
              {t.dailyReports.nap} ({t.dailyReports.napMinutes})
            </span>
            <input
              className="input"
              type="number"
              min={0}
              max={1440}
              readOnly={readOnly}
              defaultValue={nap}
              onChange={(e) => (nap = e.target.value)}
            />
          </label>

          <label className="field">
            <span className="field__label">{t.dailyReports.activities}</span>
            <textarea
              className="input"
              rows={3}
              maxLength={4000}
              readOnly={readOnly}
              defaultValue={activities}
              onChange={(e) => (activities = e.target.value)}
            />
            <p className="hint">{t.dailyReports.activitiesHint}</p>
          </label>

          <label className="field">
            <span className="field__label">{t.dailyReports.teacherNote}</span>
            <textarea
              className="input"
              rows={2}
              maxLength={2000}
              readOnly={readOnly}
              defaultValue={note}
              onChange={(e) => (note = e.target.value)}
            />
            <p className="hint">{t.dailyReports.teacherNoteHint}</p>
          </label>

          <label className="field">
            <span className="field__label">{t.dailyReports.summary}</span>
            <textarea
              className="input"
              rows={3}
              maxLength={4000}
              readOnly={readOnly}
              defaultValue={summary}
              onChange={(e) => (summary = e.target.value)}
            />
            <p className="hint">{t.dailyReports.summaryHint}</p>
          </label>

          {error && <p className="error" role="alert">{error}</p>}
          {!readOnly && (
            <div className="modal-actions">
              <button className="btn btn--full" type="submit" disabled={saving}>
                {saving ? t.common.saving : t.common.save}
              </button>
            </div>
          )}
        </form>,
        {
          title: row.child_name,
          subtitle: `${t.dailyReports.title} — ${date}`,
          size: "default",
        },
      );
    }

    render();
  }

  async function onPublish(report: DailyReport): Promise<void> {
    // Backend ham tekshiradi, lekin bu yerda oldindan aytish tushunarliroq:
    // bo'sh hisobot e'lon qilinmaydi (matnsiz xabar ota-onaga foydasiz).
    if (!report.final_summary && !report.activities_text) {
      toast.show(t.dailyReports.needText, { type: "neg" });
      return;
    }
    const ok = await confirm({
      title: t.dailyReports.publishConfirm,
      body: t.dailyReports.publishConfirmBody,
      confirmLabel: t.dailyReports.publish,
      cancelLabel: t.common.cancel,
    });
    if (!ok) return;

    setBusy(report.id);
    try {
      await api.publishDailyReport(report.id);
      toast.show(t.dailyReports.publishedToast);
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, {
        type: "neg",
      });
    } finally {
      setBusy("");
    }
  }

  const publishedCount = roster.filter((r) => r.report?.is_published).length;
  const draftCount = roster.filter(
    (r) => r.report && !r.report.is_published,
  ).length;
  const missingCount = roster.filter((r) => !r.report).length;

  function statusBadge(row: DailyReportRosterRow): ReactNode {
    if (!row.report) {
      return (
        <span className="badge badge--mute">{t.dailyReports.notWritten}</span>
      );
    }
    return row.report.is_published ? (
      <span className="badge badge--pos">{t.dailyReports.published}</span>
    ) : (
      <span className="badge badge--warn">{t.dailyReports.draft}</span>
    );
  }

  return (
    <>
      <div className="card">
        {/* Guruh va sana bitta qatorda: guruhlar ko'p bo'lsa ham qator
            o'ralmaydi, gorizontal suriladi (GroupPicker). */}
        <div className="toolbar toolbar--picker">
          <GroupPicker
            groups={groups}
            value={groupId}
            onChange={setGroupId}
            labels={groupPickerLabels(t)}
          />
          <input
            className="input toolbar__date"
            type="date"
            aria-label={t.common.date}
            title={t.common.date}
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>

        <div className="att__sum">
          <div>
            {t.dailyReports.countDone}
            <b style={{ color: "var(--pos)" }}>{publishedCount}</b>
          </div>
          <div>
            {t.dailyReports.countDraft}
            <b style={{ color: "var(--warn)" }}>{draftCount}</b>
          </div>
          <div>
            {t.dailyReports.countMissing}
            <b style={{ color: "var(--ink-2)" }}>{missingCount}</b>
          </div>
        </div>

        {loadError ? (
          <LoadError error={loadError} onRetry={load} />
        ) : !ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : roster.length === 0 ? (
          <EmptyState title={t.common.empty} />
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.common.name}</th>
                  <th className="dr-col-status">{t.common.status}</th>
                  <th className="r" />
                </tr>
              </thead>
              <tbody>
                {roster.map((row) => (
                  <tr key={row.child_id}>
                    <td>
                      <div className="cell-name">
                        <span className="avatar">
                          {initials(row.child_name)}
                        </span>
                        <div>
                          <b className="tr">{row.child_name}</b>
                          <div className="dr-status-inline">
                            {statusBadge(row)}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="dr-col-status">{statusBadge(row)}</td>
                    <td className="r">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="btn btn-ghost btn--sm"
                          onClick={() => openForm(row)}
                        >
                          {!row.report
                            ? t.dailyReports.write
                            : row.report.is_published
                              ? t.dailyReports.view
                              : t.dailyReports.edit}
                        </button>
                        {row.report && !row.report.is_published && (
                          <button
                            type="button"
                            className="btn btn--sm"
                            disabled={busy === row.report.id}
                            onClick={() =>
                              void onPublish(row.report as DailyReport)
                            }
                          >
                            {busy === row.report.id
                              ? t.dailyReports.publishing
                              : t.dailyReports.publish}
                          </button>
                        )}
                      </div>
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
