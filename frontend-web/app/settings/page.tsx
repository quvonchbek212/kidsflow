"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { useAppUI } from "@/components/AppShell";
import { NotificationSettingsCard } from "@/components/NotificationSettingsCard";
import type { AppStrings } from "@/lib/app-i18n";
import { LoadError, logSecondaryFailure } from "@/components/ui/LoadError";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError, api, type Branch, type Group } from "@/lib/api";
import { money } from "@/lib/format";

export default function SettingsPage(): ReactNode {
  return <SettingsContent />;
}

/** Filial yaratish/tahrirlash oynasi. Modal ichida o'z holatini boshqaradi
 *  (ModalProvider kontentni bir marta "suratga oladi"). */
function BranchForm({
  existing,
  t,
  onSaved,
}: {
  existing: Branch | null;
  t: AppStrings;
  onSaved: () => void;
}): ReactNode {
  const [name, setName] = useState(existing?.name ?? "");
  const [address, setAddress] = useState(existing?.address ?? "");
  const [phone, setPhone] = useState(existing?.phone ?? "");
  const [capacity, setCapacity] = useState(
    existing?.capacity != null ? String(existing.capacity) : "",
  );
  const [isActive, setIsActive] = useState(existing?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent): Promise<void> {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        name: name.trim(),
        address: address.trim() || null,
        phone: phone.trim() || null,
        capacity: capacity.trim() ? Number(capacity) : null,
      };
      if (existing) {
        await api.updateBranch(existing.id, {
          ...payload,
          is_active: isActive,
        });
      } else {
        await api.createBranch(payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.common.errTitle);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <label className="field">
        <span className="field__label">
          {t.settings.branchName}
          <span className="req">*</span>
        </span>
        <input
          className="input"
          required
          maxLength={255}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className="field">
        <span className="field__label">{t.settings.address}</span>
        <input
          className="input"
          maxLength={500}
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
      </label>
      <label className="field">
        <span className="field__label">{t.common.phone}</span>
        <input
          className="input"
          placeholder="+998 90 123 45 67"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
      </label>
      <label className="field">
        <span className="field__label">{t.settings.branchCapacity}</span>
        <input
          className="input"
          type="number"
          min={1}
          value={capacity}
          onChange={(e) => setCapacity(e.target.value)}
        />
      </label>

      {/* Filial o'chirilmaydi — faolsizlantiriladi. Undagi guruhlar, bolalar va
          moliyaviy tarix saqlanib qoladi (11-bo'lim: yozuvlar o'chirilmaydi). */}
      {existing && (
        <label className="check">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span>{t.common.active}</span>
        </label>
      )}

      {error && <p className="error" role="alert">{error}</p>}
      <div className="modal-actions">
        <button className="btn btn--full" type="submit" disabled={saving}>
          {saving ? t.common.saving : t.common.save}
        </button>
      </div>
    </form>
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
  const [branches, setBranches] = useState<Branch[]>([]);
  const modal = useModal();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [loadError, setLoadError] = useState<unknown>(null);
  const [hoursText, setHoursText] = useState("");

  const loadSettings = useCallback((): void => {
    setLoadError(null);
    api
      .getSettings()
      .then((s) => {
        setName(s.name);
        setLegalName(s.legal_name ?? "");
        setAddress(s.address ?? "");
        setPhone(s.phone ?? "");
        setHoursText(s.hours_text ?? "");
      })
      .catch(setLoadError)
      .finally(() => setReady(true));
  }, []);

  useEffect(loadSettings, [loadSettings]);

  useEffect(() => {
    if (!branchId) return;
    api
      .listGroups(branchId)
      .then((list) => setGroups(list.filter((g) => g.is_active)))
      .catch(logSecondaryFailure("Guruhlar ro'yxati"));
  }, [branchId]);

  const loadBranches = useCallback((): void => {
    api
      .listBranches()
      .then(setBranches)
      .catch(logSecondaryFailure("Filiallar ro'yxati"));
  }, []);

  useEffect(loadBranches, [loadBranches]);

  function openBranch(existing: Branch | null): void {
    modal.open(
      <BranchForm
        existing={existing}
        t={t}
        onSaved={() => {
          modal.close();
          toast.show(t.settings.branchSaved);
          loadBranches();
        }}
      />,
      {
        title: existing ? t.settings.editBranch : t.settings.newBranch,
        subtitle: existing?.name,
        size: "narrow",
      },
    );
  }

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
      });
      toast.show(t.settings.saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.common.errTitle);
    } finally {
      setSaving(false);
    }
  }

  if (loadError) {
    return <LoadError error={loadError} onRetry={loadSettings} />;
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
                <label className="field span-2">
                  <span className="field__label">
                    {t.settings.name}
                    <span className="req">*</span>
                  </span>
                  <input
                    className="input"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </label>
                <label className="field span-2">
                  <span className="field__label">{t.settings.legalName}</span>
                  <input
                    className="input"
                    value={legalName}
                    onChange={(e) => setLegalName(e.target.value)}
                  />
                </label>
                <label className="field span-2">
                  <span className="field__label">{t.settings.address}</span>
                  <input
                    className="input"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field__label">{t.common.phone}</span>
                  <input
                    className="input"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field__label">{t.settings.hoursText}</span>
                  <input
                    className="input"
                    placeholder="07:30 — 18:30"
                    value={hoursText}
                    onChange={(e) => setHoursText(e.target.value)}
                  />
                </label>
              </div>
              {error && <p className="error" role="alert">{error}</p>}
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
            <EmptyState title={t.common.empty} />
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

      <NotificationSettingsCard branchId={branchId} t={t} />

      {/* Filiallar — har biri o'z guruhlari, xodimlari va hisobotiga ega.
          Yon paneldagi filial tanlagichi shu ro'yxatdan to'ldiriladi. */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card__head">
          <div>
            <h3>{t.settings.branchesSection}</h3>
            <p>{t.settings.branchesSub}</p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => openBranch(null)}
          >
            + {t.settings.addBranch}
          </button>
        </div>
        {branches.length === 0 ? (
          <EmptyState title={t.common.empty} />
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.settings.branchName}</th>
                  <th>{t.settings.address}</th>
                  <th>{t.common.phone}</th>
                  <th className="r">{t.settings.branchCapacity}</th>
                  <th className="r" />
                </tr>
              </thead>
              <tbody>
                {branches.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <b>{b.name}</b>
                      {!b.is_active && (
                        <>
                          {" "}
                          <span className="badge badge--mute">
                            {t.settings.branchInactive}
                          </span>
                        </>
                      )}
                    </td>
                    <td className="muted">{b.address ?? "—"}</td>
                    <td className="num muted">{b.phone ?? "—"}</td>
                    <td className="r num">{b.capacity ?? "—"}</td>
                    <td className="r">
                      <button
                        type="button"
                        className="btn btn-ghost btn--sm"
                        onClick={() => openBranch(b)}
                      >
                        {t.common.edit}
                      </button>
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
