"use client";

/**
 * Sozlamalar sahifasidagi eslatma kunlari kartochkasi.
 *
 * FILIAL kesimida — yon paneldagi filial almashsa, ma'lumot ham almashadi.
 * Bayram tabriklari bu yerda sozlanmaydi: ular "Ota-onalar" bo'limidagi
 * ommaviy xabar formasi orqali qo'lda yuboriladi.
 */

import { useCallback, useEffect, useState, type ReactNode } from "react";

import { logSecondaryFailure } from "@/components/ui/LoadError";
import { useToast } from "@/components/ui/ToastProvider";
import { ApiError, api, type BranchNotificationSettings } from "@/lib/api";
import type { AppStrings } from "@/lib/app-i18n";

export function NotificationSettingsCard({
  branchId,
  t,
}: {
  branchId: string;
  t: AppStrings;
}): ReactNode {
  const toast = useToast();
  const [settings, setSettings] = useState<BranchNotificationSettings | null>(
    null,
  );

  const load = useCallback((): void => {
    if (!branchId) return;
    api
      .notificationSettings(branchId)
      .then(setSettings)
      .catch(logSecondaryFailure("Bildirishnoma sozlamalari"));
  }, [branchId]);

  useEffect(load, [load]);

  function fail(err: unknown): void {
    toast.show(err instanceof ApiError ? err.message : t.common.errTitle, {
      type: "neg",
    });
  }

  async function saveDays(
    field:
      | "payment_reminder_days_before"
      | "debt_warning_days_late"
      | "invoice_due_day",
    value: string,
  ): Promise<void> {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) return;
    try {
      setSettings(
        await api.updateNotificationSettings(branchId, { [field]: parsed }),
      );
    } catch (err) {
      fail(err);
    }
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="card__head">
        <div>
          <h3>{t.messaging.reminderDaysTitle}</h3>
          <p>{t.messaging.reminderDaysSub}</p>
        </div>
      </div>
      <div className="card__body">
        <div className="form-grid form-grid--3">
          <label className="field">
            <span className="field__label">{t.messaging.reminderBefore}</span>
            <input
              className="input"
              type="number"
              min={0}
              max={60}
              value={settings?.payment_reminder_days_before ?? 5}
              onChange={(e) =>
                setSettings((prev) =>
                  prev
                    ? {
                        ...prev,
                        payment_reminder_days_before: Number(e.target.value),
                      }
                    : prev,
                )
              }
              onBlur={(e) =>
                saveDays("payment_reminder_days_before", e.target.value)
              }
            />
          </label>
          <label className="field">
            <span className="field__label">{t.messaging.reminderLate}</span>
            <input
              className="input"
              type="number"
              min={1}
              max={180}
              value={settings?.debt_warning_days_late ?? 15}
              onChange={(e) =>
                setSettings((prev) =>
                  prev
                    ? { ...prev, debt_warning_days_late: Number(e.target.value) }
                    : prev,
                )
              }
              onBlur={(e) => saveDays("debt_warning_days_late", e.target.value)}
            />
          </label>
          {/* Hisob-fakturalar avtomatik yaratiladi — muddat shu yerdan. */}
          <label className="field">
            <span className="field__label">{t.messaging.invoiceDueDay}</span>
            <input
              className="input"
              type="number"
              min={1}
              max={28}
              value={settings?.invoice_due_day ?? 10}
              onChange={(e) =>
                setSettings((prev) =>
                  prev
                    ? { ...prev, invoice_due_day: Number(e.target.value) }
                    : prev,
                )
              }
              onBlur={(e) => saveDays("invoice_due_day", e.target.value)}
            />
          </label>
        </div>
      </div>
    </div>
  );
}
