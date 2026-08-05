"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { useConfirm } from "@/components/ui/useConfirm";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type EmploymentType,
  type PayrollRun,
  type PayrollSummary,
  type StaffUser,
} from "@/lib/api";
import { initials, money, monthRange } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

const POSITIONS = ["MANAGER", "TEACHER", "COOK", "CLEANER", "NURSE", "ASSISTANT"] as const;

export default function StaffPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="staff">
      <Suspense fallback={null}>
        <StaffContent />
      </Suspense>
    </AppShell>
  );
}

function StaffContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.staff.title, subtitle: t.staff.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [staff, setStaff] = useState<StaffUser[]>([]);
  const [payroll, setPayroll] = useState<PayrollSummary | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [ready, setReady] = useState(false);

  function load(): void {
    setReady(false);
    api
      .listStaff()
      .then((list) => {
        setStaff(list);
        setForbidden(false);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) setForbidden(true);
      })
      .finally(() => setReady(true));
    api
      .payrollSummary()
      .then(setPayroll)
      .catch(() => {});
  }

  useEffect(load, []);

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      openStaffForm(null);
      router.replace("/staff");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function employmentLabel(v: EmploymentType | null): string {
    if (v === "FULL_TIME") return t.staff.fullTime;
    if (v === "PART_TIME") return t.staff.partTime;
    if (v === "HOURLY") return t.staff.hourly;
    return "—";
  }

  function openStaffForm(existing: StaffUser | null): void {
    let fullName = existing?.full_name ?? "";
    let username = "";
    let phone = existing?.phone ?? "";
    let email = existing?.email ?? "";
    let password = "";
    let role = "TEACHER";
    let position = existing?.position ?? "TEACHER";
    let salary = existing?.monthly_salary ?? "";
    let birthDate = existing?.birth_date ?? "";
    let passportNumber = existing?.passport_number ?? "";
    let hireDate = existing?.hire_date ?? "";
    let employmentType: EmploymentType | "" = existing?.employment_type ?? "";
    let saving = false;
    let error = "";

    function render(): void {
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            saving = true;
            error = "";
            render();
            try {
              if (existing) {
                await api.updateStaff(existing.id, {
                  full_name: fullName,
                  phone: phone || undefined,
                  email: email || undefined,
                  position,
                  monthly_salary: salary || undefined,
                  birth_date: birthDate || undefined,
                  passport_number: passportNumber || undefined,
                  hire_date: hireDate || undefined,
                  employment_type: employmentType || undefined,
                });
              } else {
                await api.createStaff({
                  full_name: fullName,
                  username,
                  phone: phone || undefined,
                  email: email || undefined,
                  password,
                  role,
                  position,
                  branch_id: branchId || undefined,
                  monthly_salary: salary || undefined,
                  birth_date: birthDate || undefined,
                  passport_number: passportNumber || undefined,
                  hire_date: hireDate || undefined,
                  employment_type: employmentType || undefined,
                });
              }
              modal.close();
              toast.show(t.staff.savedStaff);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-sec">{t.staff.personalInfo}</div>
          <div className="form-grid">
            <div className="field span-2">
              <label>
                {t.common.fullName}
                <span className="req">*</span>
              </label>
              <input className="input" defaultValue={fullName} required onChange={(e) => (fullName = e.target.value)} />
            </div>
            <div className="field">
              <label>{t.common.birthDate}</label>
              <input className="input" type="date" defaultValue={birthDate} onChange={(e) => (birthDate = e.target.value)} />
            </div>
            <div className="field">
              <label>{t.staff.passportNumber}</label>
              <input
                className="input"
                defaultValue={passportNumber}
                onChange={(e) => (passportNumber = e.target.value)}
              />
            </div>
          </div>

          <div className="form-sec">{t.staff.workInfo}</div>
          <div className="form-grid">
            <div className="field">
              <label>{t.staff.position}</label>
              <select className="input" defaultValue={position} onChange={(e) => (position = e.target.value)}>
                {POSITIONS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>
                {t.staff.salary} ({t.common.sum})
              </label>
              <input className="input" inputMode="decimal" defaultValue={salary} onChange={(e) => (salary = e.target.value)} />
            </div>
            <div className="field">
              <label>{t.staff.hireDate}</label>
              <input className="input" type="date" defaultValue={hireDate} onChange={(e) => (hireDate = e.target.value)} />
            </div>
            <div className="field">
              <label>{t.staff.employmentType}</label>
              <select
                className="input"
                defaultValue={employmentType}
                onChange={(e) => (employmentType = e.target.value as EmploymentType)}
              >
                <option value="">—</option>
                <option value="FULL_TIME">{t.staff.fullTime}</option>
                <option value="PART_TIME">{t.staff.partTime}</option>
                <option value="HOURLY">{t.staff.hourly}</option>
              </select>
            </div>
          </div>

          {!existing && (
            <>
              <div className="form-sec">{t.staff.accessInfo}</div>
              <div className="form-grid">
                <div className="field">
                  <label>
                    {t.staff.login}
                    <span className="req">*</span>
                  </label>
                  <input className="input" required minLength={3} onChange={(e) => (username = e.target.value)} />
                </div>
                <div className="field">
                  <label>{t.common.phone}</label>
                  <input className="input" defaultValue={phone} onChange={(e) => (phone = e.target.value)} />
                </div>
                <div className="field">
                  <label>{t.common.email}</label>
                  <input className="input" type="email" defaultValue={email} onChange={(e) => (email = e.target.value)} />
                </div>
                <div className="field">
                  <label>
                    {t.staff.password}
                    <span className="req">*</span>
                  </label>
                  <input
                    className="input"
                    type="password"
                    required
                    minLength={8}
                    onChange={(e) => (password = e.target.value)}
                  />
                </div>
                <div className="field span-2">
                  <label>{t.common.role}</label>
                  <select className="input" defaultValue={role} onChange={(e) => (role = e.target.value)}>
                    <option value="OWNER">{t.roleLabels.OWNER}</option>
                    <option value="MANAGER">{t.roleLabels.MANAGER}</option>
                    <option value="TEACHER">{t.roleLabels.TEACHER}</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {error && <p className="error">{error}</p>}
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button className="btn" type="submit" disabled={saving} style={{ flex: 1 }}>
              {saving ? t.common.saving : existing ? t.common.save : t.common.create}
            </button>
            {existing && existing.is_active && (
              <button
                type="button"
                className="btn--quiet btn"
                style={{ color: "var(--neg)" }}
                onClick={async () => {
                  const ok = await confirm({
                    title: t.common.deactivateTitle,
                    body: t.staff.deactivateBody,
                    confirmLabel: t.common.deactivate,
                    cancelLabel: t.common.cancel,
                    danger: true,
                  });
                  if (!ok) return;
                  await api.updateStaff(existing.id, { is_active: false });
                  modal.close();
                  toast.show(t.common.saved);
                  load();
                }}
              >
                {t.common.deactivate}
              </button>
            )}
          </div>
        </form>,
        { title: existing ? t.staff.editStaff : t.staff.addStaff, size: "wide" },
      );
    }
    render();
  }

  function payrollStatusLabel(status: string): string {
    return status === "REVERSED" ? t.staff.payrollReversed : t.staff.payrollRecorded;
  }

  function openPayrollModal(staffMember: StaffUser): void {
    let baseSalary = staffMember.monthly_salary ?? "";
    let bonus = "0";
    let deduction = "0";
    let advanceDeducted = "0";
    const period = monthRange().start;
    let saving = false;
    let error = "";
    let runs: PayrollRun[] = [];
    let historyReady = false;

    function loadHistory(): void {
      api
        .listPayrollRuns({ user_id: staffMember.id })
        .then((list) => {
          runs = list;
        })
        .catch(() => {})
        .finally(() => {
          historyReady = true;
          render();
        });
    }

    function netPay(): number {
      return (
        Number(baseSalary || 0) + Number(bonus || 0) - Number(deduction || 0) - Number(advanceDeducted || 0)
      );
    }

    function render(): void {
      modal.open(
        <div>
          <form
            onSubmit={async (e: FormEvent) => {
              e.preventDefault();
              saving = true;
              error = "";
              render();
              try {
                await api.createPayrollRun({
                  branch_id: branchId,
                  user_id: staffMember.id,
                  period,
                  base_salary: baseSalary || undefined,
                  bonus,
                  deduction,
                  advance_deducted: advanceDeducted,
                  paid_at: new Date().toISOString(),
                });
                toast.show(t.staff.payrollSaved);
                loadHistory();
              } catch (err) {
                error = err instanceof ApiError ? err.message : t.common.errTitle;
              } finally {
                saving = false;
                render();
              }
            }}
          >
            <div className="form-grid">
              <div className="field">
                <label>{t.staff.payrollPeriod}</label>
                <input className="input" value={period} disabled />
              </div>
              <div className="field">
                <label>
                  {t.staff.baseSalary} ({t.common.sum})
                </label>
                <input
                  className="input"
                  inputMode="decimal"
                  defaultValue={baseSalary}
                  onChange={(e) => {
                    baseSalary = e.target.value;
                    render();
                  }}
                />
              </div>
              <div className="field">
                <label>{t.staff.bonus}</label>
                <input
                  className="input"
                  inputMode="decimal"
                  defaultValue={bonus}
                  onChange={(e) => {
                    bonus = e.target.value;
                    render();
                  }}
                />
              </div>
              <div className="field">
                <label>{t.staff.deduction}</label>
                <input
                  className="input"
                  inputMode="decimal"
                  defaultValue={deduction}
                  onChange={(e) => {
                    deduction = e.target.value;
                    render();
                  }}
                />
              </div>
              <div className="field">
                <label>{t.staff.advanceDeducted}</label>
                <input
                  className="input"
                  inputMode="decimal"
                  defaultValue={advanceDeducted}
                  onChange={(e) => {
                    advanceDeducted = e.target.value;
                    render();
                  }}
                />
              </div>
            </div>
            <div className="kpi" style={{ marginTop: 8, marginBottom: 16 }}>
              <div className="kpi__top">
                <span className="kpi__label">{t.staff.netPay}</span>
              </div>
              <div className="kpi__value">{money(netPay())}</div>
            </div>
            {error && <p className="error">{error}</p>}
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.staff.payrollRunAction}
            </button>
          </form>

          <div className="form-sec">{t.staff.payrollHistory}</div>
          {!historyReady ? (
            <p className="muted">{t.common.loading}</p>
          ) : runs.length === 0 ? (
            <p className="muted">{t.common.empty}</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>{t.staff.payrollPeriod}</th>
                  <th>{t.staff.netPay}</th>
                  <th>{t.staff.payrollStatus}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td>{r.period}</td>
                    <td>{money(r.net_pay)}</td>
                    <td>{payrollStatusLabel(r.status)}</td>
                    <td>
                      {r.status === "RECORDED" && (
                        <button
                          type="button"
                          className="btn-ghost btn-sm btn"
                          onClick={async () => {
                            const ok = await confirm({
                              title: t.common.reverseTitle,
                              body: t.staff.payrollReverseConfirm,
                              confirmLabel: t.common.reverse,
                              cancelLabel: t.common.cancel,
                              danger: true,
                            });
                            if (!ok) return;
                            await api.reversePayrollRun(r.id);
                            toast.show(t.common.reverseDone);
                            loadHistory();
                          }}
                        >
                          {t.common.reverse}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>,
        { title: t.staff.payrollRunTitle, size: "wide" },
      );
    }
    loadHistory();
    render();
  }

  const columns: DataTableColumn<StaffUser>[] = [
    {
      key: "name",
      label: t.common.fullName,
      sortValue: (s) => s.full_name,
      render: (s) => (
        <div className="cell-name">
          <span className="avatar">{initials(s.full_name)}</span>
          <b className="tr">{s.full_name}</b>
        </div>
      ),
    },
    { key: "position", label: t.staff.position, sortValue: (s) => s.position ?? "", render: (s) => s.position ?? "—" },
    { key: "employment", label: t.staff.employmentType, render: (s) => employmentLabel(s.employment_type) },
    {
      key: "salary",
      label: t.staff.salary,
      align: "right",
      sortValue: (s) => Number(s.monthly_salary ?? 0),
      render: (s) => (s.monthly_salary ? money(s.monthly_salary) : "—"),
    },
    {
      key: "status",
      label: t.common.status,
      align: "right",
      render: (s) =>
        s.is_active ? (
          <span className="badge badge--pos">{t.common.active}</span>
        ) : (
          <span className="badge badge--mute">{t.common.inactive}</span>
        ),
    },
    {
      key: "payrollAction",
      label: "",
      align: "right",
      render: (s) => (
        <button
          type="button"
          className="btn-ghost btn-sm btn"
          onClick={(e) => {
            e.stopPropagation();
            openPayrollModal(s);
          }}
        >
          {t.staff.payrollRunAction}
        </button>
      ),
    },
  ];

  return (
    <>

      {payroll && (
        <div className="kpi" style={{ maxWidth: 260, marginBottom: 16 }}>
          <div className="kpi__top">
            <span className="kpi__label">{t.staff.payrollFund}</span>
          </div>
          <div className="kpi__value">{money(payroll.total_fund)}</div>
        </div>
      )}

      {!ready ? (
        <div className="card">
          <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
            <div className="sk sk-line" style={{ width: "40%" }} />
          </div>
        </div>
      ) : forbidden ? (
        <div className="card">
          <div className="panel-empty">{t.common.errTitle}</div>
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={staff}
          rowKey={(s) => s.id}
          searchText={(s) => `${s.full_name} ${s.position ?? ""}`}
          searchPlaceholder={t.common.search}
          filters={[{ key: "all", label: t.staff.filterAll }, ...POSITIONS.map((p) => ({ key: p, label: p }))]}
          filterFn={(s, f) => s.position === f}
          onRowClick={(s) => openStaffForm(s)}
          emptyTitle={t.common.nothingFound}
          emptySub={t.common.nothingFoundSub}
          clearFiltersLabel={t.common.clearFilters}
          showingLabel={t.common.showing}
          ofLabel={t.common.of}
          actions={
            <button type="button" className="btn btn-sm" onClick={() => openStaffForm(null)}>
              + {t.staff.addStaff}
            </button>
          }
        />
      )}
    </>
  );
}
