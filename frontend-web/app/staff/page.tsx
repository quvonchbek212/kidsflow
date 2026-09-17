"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { useAppUI } from "@/components/AppShell";
import { CountUp } from "@/components/ui/CountUp";
import { IconCheck, IconEye, IconEyeOff } from "@/components/icons";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { useConfirm } from "@/components/ui/useConfirm";
import { LoadError, logSecondaryFailure } from "@/components/ui/LoadError";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { ListSkeleton } from "@/components/ui/ListSkeleton";
import {
  ApiError,
  api,
  type EmploymentType,
  type PayrollRun,
  type SalaryAdvance,
  type PayrollSummary,
  type StaffUser,
} from "@/lib/api";
import { initials, isoDate, money, monthRange } from "@/lib/format";

const POSITIONS = [
  "MANAGER",
  "TEACHER",
  "COOK",
  "CLEANER",
  "NURSE",
  "ASSISTANT",
] as const;

export default function StaffPage(): ReactNode {
  return (
    <Suspense fallback={null}>
      <StaffContent />
    </Suspense>
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
  // Joriy oy holati jadvaldagi tugma uchun: kimga oylik hisoblangan va kim
  // oy o'rtasida avans olgan.
  const [monthRuns, setMonthRuns] = useState<Record<string, PayrollRun>>({});
  const [monthAdvances, setMonthAdvances] = useState<Record<string, number>>(
    {},
  );
  const [forbidden, setForbidden] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [ready, setReady] = useState(false);

  function load(): void {
    if (!branchId) return;
    setReady(false);
    setLoadError(null);
    api
      .listStaff(undefined, branchId)
      .then((list) => {
        setStaff(list);
        setForbidden(false);
      })
      .catch((err) => {
        // 403 alohida ishlanadi: bu nosozlik emas, huquq yetishmasligi —
        // sahifa buning uchun o'z tushuntirish blokiga ega.
        if (err instanceof ApiError && err.status === 403) setForbidden(true);
        else setLoadError(err);
      })
      .finally(() => setReady(true));
    api
      .payrollSummary(branchId)
      .then(setPayroll)
      .catch(logSecondaryFailure("Ish haqi fondi"));
    loadMonthPayroll();
  }

  function loadMonthPayroll(): void {
    if (!branchId) return;
    const period = monthRange().start;
    api
      .listPayrollRuns({ branch_id: branchId, period })
      .then((runs) => {
        const byUser: Record<string, PayrollRun> = {};
        for (const r of runs) if (r.status === "RECORDED") byUser[r.user_id] = r;
        setMonthRuns(byUser);
      })
      .catch(logSecondaryFailure("Oylik holati"));
    api
      .listSalaryAdvances({ branch_id: branchId, period })
      .then((advances) => {
        const sums: Record<string, number> = {};
        for (const a of advances) {
          if (a.status !== "RECORDED") continue;
          sums[a.user_id] = (sums[a.user_id] ?? 0) + Number(a.amount);
        }
        setMonthAdvances(sums);
      })
      .catch(logSecondaryFailure("Avanslar"));
  }

  useEffect(load, [branchId]);

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

  // Lavozim bazada enum sifatida saqlanadi (MANAGER, COOK, ...) — ekranda esa
  // tanlangan tilda ko'rsatiladi. Tarjimasi topilmasa xom qiymat qaytadi, ya'ni
  // backendga yangi lavozim qo'shilsa sahifa buzilmaydi, faqat tarjimasiz chiqadi.
  function positionLabel(v: string | null): string {
    if (!v) return "—";
    return t.staff.positionLabels[v] ?? v;
  }

  function openStaffForm(existing: StaffUser | null): void {
    let fullName = existing?.full_name ?? "";
    let username = "";
    let phone = existing?.phone ?? "";
    // Email formada so'ralmaydi. Mavjud qiymat o'zgarishsiz qaytariladi —
    // aks holda xodimni tahrirlash uni bazadan o'chirib yuborardi. Parolni
    // tiklash yo'li: menejer "Parolni o'rnatish" orqali yangi parol beradi.
    const email = existing?.email ?? "";
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
    // Mavjud xodimga yangi parol — alohida amal, umumiy "Saqlash" bilan
    // birga ketmaydi: parolni almashtirish xodimning sessiyalarini yopadi,
    // shuning uchun u ataylab alohida bosiladi.
    let newPassword = "";
    let passwordSaving = false;
    let passwordError = "";
    // Maydon `defaultValue` bilan ishlaydi — u faqat mount paytida qo'llanadi.
    // Parol saqlangach `newPassword` bo'shatilardi, lekin React DOM tugunini
    // qayta ishlatgani uchun ekranda eski parol qolib ketardi va "tugma
    // ishlamadi" degan taassurot berardi. Sanoqni oshirish maydonni qayta
    // mount qiladi, ya'ni haqiqatan tozalaydi.
    let passwordFieldKey = 0;
    let newStaffPasswordVisible = false;

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
                  // Login o'zgarmagan bo'lsa yuborilmaydi — beixtiyor
                  // "band" xatosini keltirib chiqarmasligi uchun.
                  username:
                    username && username !== existing.username
                      ? username
                      : undefined,
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
                  password,
                  phone: phone || undefined,
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
            <label className="field span-2">
              <span className="field__label">
                {t.common.fullName}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                defaultValue={fullName}
                required
                onChange={(e) => (fullName = e.target.value)}
              />
            </label>
            {/* Uchta qisqa maydon: 2 ustunli to'rda oxirgisi yolg'iz qolib,
                qatorning o'ng yarmi bo'sh turardi. Ular yonma-yon joylashadi. */}
            <div className="form-grid form-grid--3 span-2">
              <label className="field">
                <span className="field__label">{t.common.birthDate}</span>
                <input
                  className="input"
                  type="date"
                  defaultValue={birthDate}
                  onChange={(e) => (birthDate = e.target.value)}
                />
              </label>
              <label className="field">
                <span className="field__label">{t.staff.passportNumber}</span>
                <input
                  className="input"
                  defaultValue={passportNumber}
                  onChange={(e) => (passportNumber = e.target.value)}
                />
              </label>
              <label className="field">
                <span className="field__label">{t.common.phone}</span>
                <input
                  className="input"
                  type="tel"
                  placeholder="+998901234567"
                  defaultValue={phone}
                  onChange={(e) => (phone = e.target.value)}
                />
              </label>
            </div>
          </div>

          <div className="form-sec">{t.staff.workInfo}</div>
          <div className="form-grid">
            <label className="field">
              <span className="field__label">{t.staff.position}</span>
              <select
                className="input"
                defaultValue={position}
                onChange={(e) => (position = e.target.value)}
              >
                {POSITIONS.map((p) => (
                  <option key={p} value={p}>
                    {positionLabel(p)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field__label">
                {t.staff.salary} ({t.common.sum})
              </span>
              <input
                className="input"
                inputMode="decimal"
                defaultValue={salary}
                onChange={(e) => (salary = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.staff.hireDate}</span>
              <input
                className="input"
                type="date"
                defaultValue={hireDate}
                onChange={(e) => (hireDate = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.staff.employmentType}</span>
              <select
                className="input"
                defaultValue={employmentType}
                onChange={(e) =>
                  (employmentType = e.target.value as EmploymentType)
                }
              >
                <option value="">—</option>
                <option value="FULL_TIME">{t.staff.fullTime}</option>
                <option value="PART_TIME">{t.staff.partTime}</option>
                <option value="HOURLY">{t.staff.hourly}</option>
              </select>
            </label>
          </div>

          {!existing && (
            <>
              <div className="form-sec">{t.staff.accessInfo}</div>
              <div className="form-grid">
                {/* Login va parol — har biri alohida qatorda. Ular xodimga
                    aytiladigan yagona narsa, shuning uchun boshqa maydonlar
                    orasida siqilib qolmasligi kerak. */}
                <label className="field span-2">
                  <span className="field__label">
                    {t.staff.login}
                    <span className="req">*</span>
                  </span>
                  <input
                    className="input"
                    defaultValue={username}
                    required
                    minLength={3}
                    autoComplete="off"
                    placeholder="masalan: dilnoza.karimova"
                    onChange={(e) => (username = e.target.value)}
                  />
                  <p className="field__hint">{t.staff.loginHint}</p>
                </label>
                <div className="field span-2">
                  <label htmlFor="staff-new-password">
                    {t.staff.password}
                    <span className="req">*</span>
                  </label>
                  <div className="password-field">
                    <input
                      id="staff-new-password"
                      className="input"
                      type={newStaffPasswordVisible ? "text" : "password"}
                      defaultValue={password}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      onChange={(e) => (password = e.target.value)}
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      onClick={() => {
                        newStaffPasswordVisible = !newStaffPasswordVisible;
                        render();
                      }}
                      aria-label={
                        newStaffPasswordVisible
                          ? t.staff.hidePassword
                          : t.staff.showPassword
                      }
                      title={
                        newStaffPasswordVisible
                          ? t.staff.hidePassword
                          : t.staff.showPassword
                      }
                      aria-pressed={newStaffPasswordVisible}
                    >
                      {newStaffPasswordVisible ? (
                        <IconEyeOff size={18} />
                      ) : (
                        <IconEye size={18} />
                      )}
                    </button>
                  </div>
                  <p className="field__hint">{t.staff.passwordCreateHint}</p>
                </div>
                <label className="field span-2">
                  <span className="field__label">{t.common.role}</span>
                  <select
                    className="input"
                    defaultValue={role}
                    onChange={(e) => (role = e.target.value)}
                  >
                    <option value="OWNER">{t.roleLabels.OWNER}</option>
                    <option value="MANAGER">{t.roleLabels.MANAGER}</option>
                    <option value="TEACHER">{t.roleLabels.TEACHER}</option>
                  </select>
                </label>
              </div>
            </>
          )}

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving
                ? t.common.saving
                : existing
                  ? t.common.save
                  : t.common.create}
            </button>
            {/* Xodim o'chirilmaydi — faolsizlantiriladi: uning ish haqi
                tarixi, davomat yozuvlari va audit izlari saqlanib qolishi
                kerak. Ilgari bu yerda faqat "Faolsizlantirish" bor edi va
                nofaol xodimni UI orqali qaytarishning imkoni yo'q edi —
                hisob butunlay qulflanib qolardi. */}
            {existing && (
              <button
                type="button"
                /* Faolsizlantirish — buzuvchi amal, shuning uchun aniq qizil
                   ramka va matn (ilgari u kulrang "quiet" tugma edi va
                   oddiy amaldek ko'rinardi). Qayta faollashtirish — ijobiy,
                   yashil variantda. */
                className={
                  existing.is_active
                    ? "btn btn--outline-danger"
                    : "btn btn--outline-ok"
                }
                onClick={async () => {
                  const turningOff = existing.is_active;
                  const ok = await confirm({
                    title: turningOff
                      ? t.common.deactivateTitle
                      : t.common.activateTitle,
                    body: turningOff
                      ? t.staff.deactivateBody
                      : t.staff.activateBody,
                    confirmLabel: turningOff
                      ? t.common.deactivate
                      : t.common.activate,
                    cancelLabel: t.common.cancel,
                    danger: turningOff,
                  });
                  if (!ok) return;
                  await api.updateStaff(existing.id, {
                    is_active: !turningOff,
                  });
                  modal.close();
                  toast.show(t.common.saved);
                  load();
                }}
              >
                {existing.is_active ? t.common.deactivate : t.common.activate}
              </button>
            )}
          </div>

          {existing && (
            <>
              <div className="form-sec">{t.staff.accessInfo}</div>
              {/* Loginni menejer/egasi almashtira oladi: xodim uni unutsa
                  yoki xato yozilgan bo'lsa tuzatish kerak. O'zgarish umumiy
                  "Saqlash" bilan yuboriladi. */}
              <label className="field">
                <span className="field__label">{t.staff.login}</span>
                <input
                  className="input"
                  defaultValue={existing.username ?? ""}
                  minLength={3}
                  autoComplete="off"
                  onChange={(e) => (username = e.target.value)}
                />
                <span className="field__hint">{t.staff.loginHint}</span>
              </label>

              <div className="form-sec">{t.staff.newPassword}</div>
              <p className="muted" style={{ fontSize: 12.5, marginTop: 0 }}>
                {t.staff.passwordHint}
              </p>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                  <input
                    key={passwordFieldKey}
                    className="input"
                    type="password"
                    defaultValue={newPassword}
                    autoComplete="new-password"
                    onChange={(e) => (newPassword = e.target.value)}
                  />
                </div>
                <button
                  type="button"
                  className="btn-ghost btn"
                  disabled={passwordSaving}
                  onClick={async () => {
                    if (newPassword.length < 8) {
                      passwordError = t.staff.passwordTooShort;
                      render();
                      return;
                    }
                    passwordSaving = true;
                    passwordError = "";
                    render();
                    try {
                      await api.setStaffPassword(existing.id, newPassword);
                      newPassword = "";
                      passwordFieldKey += 1;
                      toast.show(t.staff.passwordSet);
                    } catch (err) {
                      passwordError =
                        err instanceof ApiError
                          ? err.message
                          : t.common.errTitle;
                    } finally {
                      passwordSaving = false;
                      render();
                    }
                  }}
                >
                  {passwordSaving ? t.common.saving : t.staff.setPassword}
                </button>
              </div>
              {passwordError && (
                <p className="error" role="alert">
                  {passwordError}
                </p>
              )}
            </>
          )}
        </form>,
        {
          title: existing ? t.staff.editStaff : t.staff.addStaff,
          size: "wide",
        },
      );
    }
    render();
  }

  function payrollStatusLabel(status: string): string {
    return status === "REVERSED"
      ? t.staff.payrollReversed
      : t.staff.payrollRecorded;
  }

  function openPayrollModal(staffMember: StaffUser): void {
    let baseSalary = staffMember.monthly_salary ?? "";
    let bonus = "0";
    let deduction = "0";
    const period = monthRange().start;
    let saving = false;
    let error = "";
    let runs: PayrollRun[] = [];
    let advances: SalaryAdvance[] = [];
    let historyReady = false;

    // Avans formasi
    let advanceAmount = "";
    let advanceDate = isoDate(new Date());
    let advanceSaving = false;
    let advanceError = "";
    // Avans saqlangach maydonni tozalash uchun: `defaultValue` qayta
    // chizishda o'zgarmaydi, kalit almashsa esa input yangidan yaratiladi.
    let advanceFormKey = 0;

    function loadHistory(): void {
      Promise.all([
        api.listPayrollRuns({ user_id: staffMember.id }),
        api.listSalaryAdvances({ user_id: staffMember.id }),
      ])
        .then(([runList, advanceList]) => {
          runs = runList;
          advances = advanceList;
        })
        .catch(logSecondaryFailure("Ish haqi tarixi"))
        .finally(() => {
          historyReady = true;
          render();
        });
    }

    // Bir o'zgarish ham oynani, ham jadvaldagi holatni yangilaydi.
    function refresh(): void {
      loadHistory();
      loadMonthPayroll();
    }

    function activeRunFor(p: string): PayrollRun | undefined {
      return runs.find((r) => r.period === p && r.status === "RECORDED");
    }

    function advanceSum(): number {
      return advances
        .filter((a) => a.period === period && a.status === "RECORDED")
        .reduce((sum, a) => sum + Number(a.amount), 0);
    }

    function netPay(): number {
      return (
        Number(baseSalary || 0) +
        Number(bonus || 0) -
        Number(deduction || 0) -
        advanceSum()
      );
    }

    async function giveAdvance(): Promise<void> {
      if (advanceSaving || !advanceAmount) return;
      advanceSaving = true;
      advanceError = "";
      render();
      try {
        // Tanlangan kunning mahalliy tushi — UTC ga o'tganda sana (va oy)
        // surilib ketmasligi uchun.
        const paidAt = new Date(`${advanceDate}T12:00:00`).toISOString();
        await api.giveSalaryAdvance({
          branch_id: branchId,
          user_id: staffMember.id,
          amount: advanceAmount,
          paid_at: paidAt,
        });
        toast.show(t.staff.advanceGiven);
        advanceAmount = "";
        advanceFormKey += 1;
        refresh();
      } catch (err) {
        advanceError = err instanceof ApiError ? err.message : t.common.errTitle;
      } finally {
        advanceSaving = false;
        render();
      }
    }

    function render(): void {
      const currentRun = activeRunFor(period);
      const monthAdvance = advanceSum();

      modal.open(
        <div>
          {!historyReady ? (
            <p className="muted">{t.common.loading}</p>
          ) : currentRun ? (
            /* Oylik hisoblangan oy: forma o'rniga natija. Qayta hisoblash
               uchun avval tarixdan shu yozuvni bekor qilish kerak. */
            <div className="payroll-done-box">
              <div className="payroll-done-box__head">
                <span className="payroll-done-box__icon">
                  <IconCheck size={16} />
                </span>
                <b>{t.staff.payrollDoneBanner}</b>
              </div>
              <dl className="payroll-done-box__grid">
                <div>
                  <dt>{t.staff.netPay}</dt>
                  <dd>{money(currentRun.net_pay)}</dd>
                </div>
                <div>
                  <dt>{t.staff.advanceDeducted}</dt>
                  <dd>{money(currentRun.advance_deducted)}</dd>
                </div>
                <div>
                  <dt>{t.staff.payrollPaidAt}</dt>
                  <dd>{currentRun.paid_at.slice(0, 10)}</dd>
                </div>
              </dl>
            </div>
          ) : (
            <>
              <div className="form-sec">{t.staff.advanceSection}</div>
              <div className="form-grid" key={advanceFormKey}>
                <label className="field">
                  <span className="field__label">
                    {t.staff.advanceAmount} ({t.common.sum})
                  </span>
                  <input
                    className="input"
                    inputMode="decimal"
                    defaultValue={advanceAmount}
                    onChange={(e) => {
                      advanceAmount = e.target.value;
                      render();
                    }}
                  />
                </label>
                <label className="field">
                  <span className="field__label">{t.staff.advanceDate}</span>
                  <input
                    className="input"
                    type="date"
                    defaultValue={advanceDate}
                    onChange={(e) => (advanceDate = e.target.value)}
                  />
                </label>
                <div className="field payroll-advance-action">
                  <button
                    type="button"
                    className="btn-ghost btn"
                    disabled={advanceSaving || !Number(advanceAmount)}
                    onClick={() => void giveAdvance()}
                  >
                    {advanceSaving ? t.common.saving : t.staff.advanceGive}
                  </button>
                </div>
              </div>
              {advanceError && (
                <p className="error" role="alert">
                  {advanceError}
                </p>
              )}

              <form
                onSubmit={async (e: FormEvent) => {
                  e.preventDefault();
                  saving = true;
                  error = "";
                  render();
                  try {
                    // Avans yuborilmaydi — server shu oy yozilgan avanslarni
                    // o'zi ushlaydi.
                    await api.createPayrollRun({
                      branch_id: branchId,
                      user_id: staffMember.id,
                      period,
                      base_salary: baseSalary || undefined,
                      bonus,
                      deduction,
                      paid_at: new Date().toISOString(),
                    });
                    toast.show(t.staff.payrollSaved);
                    refresh();
                  } catch (err) {
                    error =
                      err instanceof ApiError ? err.message : t.common.errTitle;
                  } finally {
                    saving = false;
                    render();
                  }
                }}
              >
                <div className="form-sec">{t.staff.payrollRunTitle}</div>
                <div className="form-grid">
                  <label className="field">
                    <span className="field__label">
                      {t.staff.payrollPeriod}
                    </span>
                    <input className="input" value={period} disabled />
                  </label>
                  <label className="field">
                    <span className="field__label">
                      {t.staff.baseSalary} ({t.common.sum})
                    </span>
                    <input
                      className="input"
                      inputMode="decimal"
                      defaultValue={baseSalary}
                      onChange={(e) => {
                        baseSalary = e.target.value;
                        render();
                      }}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">{t.staff.bonus}</span>
                    <input
                      className="input"
                      inputMode="decimal"
                      defaultValue={bonus}
                      onChange={(e) => {
                        bonus = e.target.value;
                        render();
                      }}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">{t.staff.deduction}</span>
                    <input
                      className="input"
                      inputMode="decimal"
                      defaultValue={deduction}
                      onChange={(e) => {
                        deduction = e.target.value;
                        render();
                      }}
                    />
                  </label>
                  <div className="field">
                    <span className="field__label">
                      {t.staff.advanceDeducted}
                    </span>
                    <div
                      className={`input payroll-advance-sum${monthAdvance > 0 ? " has" : ""}`}
                    >
                      {money(monthAdvance)}
                    </div>
                    <p className="hint payroll-hint">
                      {t.staff.advanceAutoHint}
                    </p>
                  </div>
                </div>
                <div className="kpi" style={{ marginTop: 8, marginBottom: 16 }}>
                  <div className="kpi__top">
                    <span className="kpi__label">{t.staff.netPay}</span>
                  </div>
                  <div className="kpi__value">{money(netPay())}</div>
                </div>
                {error && (
                  <p className="error" role="alert">
                    {error}
                  </p>
                )}
                <div className="modal-actions">
                  <button className="btn" type="submit" disabled={saving}>
                    {saving ? t.common.saving : t.staff.payrollRunAction}
                  </button>
                </div>
              </form>
            </>
          )}

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
                            try {
                              await api.reversePayrollRun(r.id);
                              toast.show(t.common.reverseDone);
                            } catch (err) {
                              toast.show(
                                err instanceof ApiError
                                  ? err.message
                                  : t.common.errTitle,
                                { type: "neg" },
                              );
                            }
                            // Tasdiq oynasi to'lov oynasini almashtirgan —
                            // xato bo'lsa ham oyna qayta chiziladi.
                            refresh();
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

          {historyReady && advances.length > 0 && (
            <>
              <div className="form-sec">{t.staff.advanceHistory}</div>
              <table>
                <thead>
                  <tr>
                    <th>{t.staff.advanceDate}</th>
                    <th>{t.staff.advanceAmount}</th>
                    <th>{t.staff.payrollStatus}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {advances.map((a) => (
                    <tr key={a.id}>
                      <td>{a.paid_at.slice(0, 10)}</td>
                      <td>{money(a.amount)}</td>
                      <td>{payrollStatusLabel(a.status)}</td>
                      <td>
                        {/* Oylik hisobida ushlangan avans bekor qilinmaydi —
                            avval o'sha oyning hisobi bekor qilinadi. */}
                        {a.status === "RECORDED" && !activeRunFor(a.period) && (
                          <button
                            type="button"
                            className="btn-ghost btn-sm btn"
                            onClick={async () => {
                              const ok = await confirm({
                                title: t.common.reverseTitle,
                                body: t.staff.advanceReverseConfirm,
                                confirmLabel: t.common.reverse,
                                cancelLabel: t.common.cancel,
                                danger: true,
                              });
                              if (!ok) return;
                              try {
                                await api.reverseSalaryAdvance(a.id);
                                toast.show(t.common.reverseDone);
                                refresh();
                              } catch (err) {
                                toast.show(
                                  err instanceof ApiError
                                    ? err.message
                                    : t.common.errTitle,
                                  { type: "neg" },
                                );
                              }
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
            </>
          )}
        </div>,
        {
          title: t.staff.payrollRunTitle,
          subtitle: staffMember.full_name,
          size: "wide",
        },
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
      // Login ismning ostida turadi: xodimga "sening logining shu" deb
      // aytish uchun uni ro'yxatdan topa olish kerak, aks holda u faqat
      // yaratish paytida bir marta ko'rinib, keyin yo'qolib ketardi.
      render: (s) => (
        // Nofaol xodim so'ndirilgan ko'rinadi — xarajatlardagi bekor qilingan
        // qator bilan bir xil uslub. Aks holda u faol xodimlardan faqat
        // o'ngdagi kichik nishon bilan farq qilardi.
        <div className="cell-name" style={{ opacity: s.is_active ? 1 : 0.55 }}>
          <span className="avatar">{initials(s.full_name)}</span>
          <div>
            <b className="tr">{s.full_name}</b>
            {s.username && <small>{s.username}</small>}
          </div>
        </div>
      ),
    },
    {
      key: "position",
      label: t.staff.position,
      // Saralash ham ko'rinadigan matn bo'yicha — foydalanuvchi "Farrosh" va
      // "Hamshira" ni alifbo tartibida kutadi, CLEANER/NURSE bo'yicha emas.
      sortValue: (s) => positionLabel(s.position),
      render: (s) => positionLabel(s.position),
    },
    {
      key: "employment",
      label: t.staff.employmentType,
      render: (s) => employmentLabel(s.employment_type),
    },
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
          <span className="badge badge--pos">
            <span className="dot" />
            {t.common.active}
          </span>
        ) : (
          /* Nofaol xodim kulrang "mute" nishonda deyarli ko'rinmasdi —
             holat ustunida u aynan ajralib turishi kerak. */
          <span className="badge badge--neg">
            <span className="dot" />
            {t.common.inactive}
          </span>
        ),
    },
    {
      key: "payrollAction",
      label: "",
      align: "right",
      render: (s) => {
        const run = monthRuns[s.id];
        const advance = monthAdvances[s.id] ?? 0;
        const label = run ? t.staff.payrollDone : t.staff.payrollRunAction;
        return (
          <div className="payroll-cell">
            {/* Oy o'rtasida olingan avans oylik hisoblanguncha ko'rinib
                turadi; hisoblangach u sof summadan ushlangan bo'ladi. */}
            {!run && advance > 0 && (
              <span className="badge badge--warn">
                {t.staff.advanceSection}: {money(advance)}
              </span>
            )}
            <button
              type="button"
              className={run ? "btn btn-sm payroll-done" : "btn-ghost btn-sm btn"}
              /* Jadvalda bu tugma har qatorda takrorlanadi — qaysi xodimga
                 tegishli ekani faqat qator kontekstidan bilinadi. Skrinrider
                 tugmalar ro'yxatini alohida o'qiganda ular farqlanmay
                 qolmasligi uchun ism nomga qo'shiladi. */
              aria-label={`${label} — ${s.full_name}`}
              title={
                run ? `${t.staff.netPay}: ${money(run.net_pay)}` : undefined
              }
              onClick={(e) => {
                e.stopPropagation();
                openPayrollModal(s);
              }}
            >
              {run && <IconCheck size={14} />}
              {label}
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <>
      {/* Kartochka doim chiziladi: ilgari u ish haqi so'rovi kelgach paydo
          bo'lib, ostidagi butun jadvalni ~160px pastga surardi (CLS). Endi
          joyi band, ichida esa qiymat o'rniga qolip turadi. */}
      {/* 280px: ish haqi fondi 30px shriftda ~222px joy egallaydi, ikki
          yonida esa 24px padding turadi (222 + 48 = 270). Ilgari kenglik
          260px edi va son sig'may ikki qatorga o'ralardi — `CountUp` sanash
          paytida har kadrda o'ralish chegarasidan o'tib, kartochka
          130↔145px sakrab, butun bo'lim qaltirab turardi. */}
      <div className="kpi" style={{ maxWidth: 280, marginBottom: 16 }}>
        <div className="kpi__top">
          <span className="kpi__label">{t.staff.payrollFund}</span>
        </div>
        {payroll ? (
          <div className="kpi__value">
            <CountUp value={Number(payroll.total_fund)} format={money} />
          </div>
        ) : (
          <div
            className="sk"
            style={{ height: 30, width: 160, marginTop: 6 }}
            aria-hidden="true"
          />
        )}
      </div>

      {loadError ? (
        <LoadError error={loadError} onRetry={load} />
      ) : !ready ? (
        <div className="card">
          <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
            <div className="sk sk-line" style={{ width: "40%" }} />
          </div>
          <ListSkeleton rows={7} />
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
          // Qidiruvda ikkalasi ham: "Tarbiyachi" deb ham, "TEACHER" deb ham topiladi.
          searchText={(s) =>
            `${s.full_name} ${s.username ?? ""} ${s.position ?? ""} ${positionLabel(s.position)}`
          }
          searchPlaceholder={t.common.search}
          filters={[
            { key: "all", label: t.staff.filterAll },
            // Holat filtri lavozimlardan oldin: faolsizlantirilgan xodim
            // ro'yxatda qolgani uchun "hech narsa o'zgarmadi" degan taassurot
            // bermasin — uni bir bosishda ajratib ko'rish mumkin.
            { key: "status:active", label: t.common.active },
            { key: "status:inactive", label: t.common.inactive },
            ...POSITIONS.map((p) => ({ key: p, label: positionLabel(p) })),
          ]}
          filterFn={(s, f) =>
            f === "status:active"
              ? s.is_active
              : f === "status:inactive"
                ? !s.is_active
                : s.position === f
          }
          onRowClick={(s) => openStaffForm(s)}
          emptyTitle={t.common.nothingFound}
          emptySub={t.common.nothingFoundSub}
          clearFiltersLabel={t.common.clearFilters}
          showingLabel={t.common.showing}
          ofLabel={t.common.of}
          actions={
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => openStaffForm(null)}
            >
              + {t.staff.addStaff}
            </button>
          }
        />
      )}
    </>
  );
}
