"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { useToast } from "@/components/ui/ToastProvider";
import { ApiError, api, type Group } from "@/lib/api";
import { money } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function SettingsPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="settings">
      <SettingsContent />
    </AppShell>
  );
}

function SettingsContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.settings.title, subtitle: t.settings.subtitle });
  }, [setPageMeta, t]);
  const toast = useToast();

  const [ready, setReady] = useState(false);
  const [groups, setGroups] = useState<Group[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [hoursText, setHoursText] = useState("");
  const [autoInvoiceDay, setAutoInvoiceDay] = useState("");

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setName(s.name);
        setLegalName(s.legal_name ?? "");
        setAddress(s.address ?? "");
        setPhone(s.phone ?? "");
        setHoursText(s.hours_text ?? "");
        setAutoInvoiceDay(s.auto_invoice_day ? String(s.auto_invoice_day) : "");
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    api
      .listGroups()
      .then((list) => setGroups(list.filter((g) => g.branch_id === branchId && g.is_active)))
      .catch(() => {});
  }, [branchId]);

  async function onSubmit(e: FormEvent): Promise<void> {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.updateSettings({
        name,
        legal_name: legalName || undefined,
        address: address || undefined,
        phone: phone || undefined,
        hours_text: hoursText || undefined,
        auto_invoice_day: autoInvoiceDay ? Number(autoInvoiceDay) : undefined,
      });
      toast.show(t.settings.saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.common.errTitle);
    } finally {
      setSaving(false);
    }
  }

  if (!ready) {
    return (
      <div className="card">
        <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
          <div className="sk sk-line" style={{ width: "40%" }} />
        </div>
      </div>
    );
  }

  return (
    <>

      {/* Mockupdagidek ikki ustun: chapda bog'cha profili, o'ngda tariflar.
          Payme/Click/2FA uchun ATAYLAB hech qanday element yo'q — loyiha qarori. */}
      <div className="grid g-2">
        <div className="card">
          <div className="card__head">
            <div>
              <h3>{t.settings.profileSection}</h3>
            </div>
          </div>
          <div className="card__body">
            <form onSubmit={onSubmit}>
              <div className="form-grid">
                <div className="field span-2">
                  <label>
                    {t.settings.name}
                    <span className="req">*</span>
                  </label>
                  <input className="input" required value={name} onChange={(e) => setName(e.target.value)} />
                </div>
                <div className="field span-2">
                  <label>{t.settings.legalName}</label>
                  <input className="input" value={legalName} onChange={(e) => setLegalName(e.target.value)} />
                </div>
                <div className="field span-2">
                  <label>{t.settings.address}</label>
                  <input className="input" value={address} onChange={(e) => setAddress(e.target.value)} />
                </div>
                <div className="field">
                  <label>{t.common.phone}</label>
                  <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
                </div>
                <div className="field">
                  <label>{t.settings.hoursText}</label>
                  <input
                    className="input"
                    placeholder="07:30 — 18:30"
                    value={hoursText}
                    onChange={(e) => setHoursText(e.target.value)}
                  />
                </div>
                <div className="field span-2">
                  <label>{t.settings.autoInvoiceDay}</label>
                  <input
                    className="input"
                    type="number"
                    min={1}
                    max={28}
                    value={autoInvoiceDay}
                    onChange={(e) => setAutoInvoiceDay(e.target.value)}
                  />
                  <p className="field__hint">{t.settings.autoInvoiceDayHint}</p>
                </div>
              </div>
              {error && <p className="error">{error}</p>}
              <button className="btn" type="submit" disabled={saving}>
                {saving ? t.common.saving : t.settings.saveChanges}
              </button>
            </form>
          </div>
        </div>

        <div className="card">
          <div className="card__head">
            <div>
              <h3>{t.settings.tariffs}</h3>
              <p>{t.settings.tariffsSub}</p>
            </div>
            <Link className="btn btn-ghost btn-sm" href="/groups">
              {t.groups.addGroup}
            </Link>
          </div>
          {groups.length === 0 ? (
            <div className="panel-empty">{t.common.empty}</div>
          ) : (
            <div className="tbl-wrap">
              <table className="tbl">
                <tbody>
                  {groups.map((g) => (
                    <tr key={g.id}>
                      <td>
                        <b>{g.name}</b>
                        <br />
                        <small className="muted">
                          {g.min_age_months != null && g.max_age_months != null
                            ? `${g.min_age_months}–${g.max_age_months} ${t.settings.months}`
                            : "—"}
                        </small>
                      </td>
                      <td className="r num" style={{ fontWeight: 600 }}>
                        {g.monthly_fee ? money(g.monthly_fee) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
