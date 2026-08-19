"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { IconUpload, IconUsers } from "@/components/icons";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { useConfirm } from "@/components/ui/useConfirm";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type Child,
  type ChildStatus,
  type DiscountType,
  type Group,
  type ImportResult,
} from "@/lib/api";
import { initials, isoDate, moneyPlain, monthRange } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function ChildrenPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="children">
      <Suspense fallback={null}>
        <ChildrenContent />
      </Suspense>
    </AppShell>
  );
}

function ChildrenContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.children.title, subtitle: t.children.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [children, setChildren] = useState<Child[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [childGroup, setChildGroup] = useState<Record<string, string>>({});
  // Mockupdagi "Telefon" va "Qarz" ustunlari uchun: telefon ota-onalar
  // ro'yxatidan, qarz esa joriy oy hisob-fakturalaridan yig'iladi.
  const [parentPhones, setParentPhones] = useState<Record<string, string>>({});
  const [childDebt, setChildDebt] = useState<Record<string, number>>({});
  const [ready, setReady] = useState(false);

  function load(): void {
    // Filial aniqlanmaguncha so'rov yuborilmaydi — aks holda server filtrsiz
    // javob qaytarib, barcha filiallar aralashib ketardi.
    if (!branchId) return;
    setReady(false);
    Promise.all([api.listChildren(branchId), api.listGroups(branchId)])
      .then(async ([childList, groupList]) => {
        setChildren(childList);

        api
          .listParents(branchId)
          .then((rows) => {
            const phones: Record<string, string> = {};
            for (const p of rows) if (p.phone) phones[p.id] = p.phone;
            setParentPhones(phones);
          })
          .catch(() => {});

        api
          .branchInvoices(branchId, monthRange().start)
          .then((invoices) => {
            const debts: Record<string, number> = {};
            for (const inv of invoices) {
              debts[inv.child_id] =
                (debts[inv.child_id] ?? 0) + Number(inv.outstanding_amount);
            }
            setChildDebt(debts);
          })
          .catch(() => {});

        // Filial kesimini server bajaradi; bu yerda faqat faollari qoladi.
        const branchGroups = groupList.filter((g) => g.is_active);
        setGroups(branchGroups);
        const rosters = await Promise.all(
          branchGroups.map((g) =>
            api
              .attendanceRoster(g.id, isoDate(new Date()))
              .then((rows) => ({ group: g, rows }))
              .catch(() => ({ group: g, rows: [] })),
          ),
        );
        const map: Record<string, string> = {};
        for (const { group, rows } of rosters) {
          for (const row of rows) map[row.child_id] = group.id;
        }
        setChildGroup(map);
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId]);

  useEffect(() => {
    if (searchParams.get("new") === "1" && groups.length >= 0) {
      openAddChild();
      router.replace("/children");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function statusBadge(status: ChildStatus): ReactNode {
    if (status === "active")
      return <span className="badge badge--pos">{t.children.active}</span>;
    if (status === "waiting")
      return <span className="badge badge--warn">{t.children.waiting}</span>;
    return <span className="badge badge--mute">{t.children.left}</span>;
  }

  const columns: DataTableColumn<Child>[] = [
    {
      key: "name",
      label: t.common.name,
      sortValue: (c) => c.full_name,
      render: (c) => (
        <div className="cell-name">
          <span className="avatar">{initials(c.full_name)}</span>
          <span>
            <b className="tr">{c.full_name}</b>
            {c.medical_notes && <small className="tr">{c.medical_notes}</small>}
          </span>
        </div>
      ),
    },
    {
      key: "group",
      label: t.children.group,
      sortValue: (c) =>
        groups.find((g) => g.id === childGroup[c.id])?.name ?? "",
      render: (c) => (
        <span style={{ color: "var(--ink-2)" }}>
          {groups.find((g) => g.id === childGroup[c.id])?.name ?? "—"}
        </span>
      ),
    },
    {
      key: "birth",
      label: t.common.birthDate,
      sortValue: (c) => c.birth_date,
      render: (c) => (
        <span className="num" style={{ color: "var(--ink-2)", fontSize: 13 }}>
          {c.birth_date}
        </span>
      ),
    },
    {
      key: "guardians",
      label: t.children.parent,
      render: (c) => (
        <span className="tr" style={{ color: "var(--ink-2)" }}>
          {(c.guardians.find((g) => g.is_primary) ?? c.guardians[0])
            ?.full_name ?? "—"}
        </span>
      ),
    },
    {
      key: "phone",
      label: t.common.phone,
      render: (c) => {
        const guardian =
          c.guardians.find((g) => g.is_primary) ?? c.guardians[0];
        const phone = guardian
          ? parentPhones[guardian.guardian_user_id]
          : undefined;
        return (
          <span className="num" style={{ fontSize: 13, color: "var(--ink-2)" }}>
            {phone ?? "—"}
          </span>
        );
      },
    },
    {
      key: "debt",
      label: t.dashboard.debt,
      align: "right",
      sortValue: (c) => childDebt[c.id] ?? 0,
      render: (c) => {
        const debt = childDebt[c.id] ?? 0;
        return (
          <span
            className="num"
            style={
              debt > 0
                ? { color: "var(--neg)", fontWeight: 600 }
                : { color: "var(--ink-3)" }
            }
          >
            {debt > 0 ? moneyPlain(debt) : "—"}
          </span>
        );
      },
    },
    {
      key: "status",
      label: t.common.status,
      align: "right",
      sortValue: (c) => c.status,
      render: (c) => statusBadge(c.status),
    },
  ];

  function openDetail(child: Child): void {
    const group = groups.find((g) => g.id === childGroup[child.id]);
    modal.open(
      <div>
        <dl className="deflist">
          <div>
            <dt>{t.common.birthDate}</dt>
            <dd>{child.birth_date}</dd>
          </div>
          <div>
            <dt>{t.children.group}</dt>
            <dd>{group?.name ?? "—"}</dd>
          </div>
          <div>
            <dt>{t.common.status}</dt>
            <dd>{statusBadge(child.status)}</dd>
          </div>
          <div>
            <dt>{t.children.medicalNotes}</dt>
            <dd>{child.medical_notes ?? "—"}</dd>
          </div>
        </dl>
        <div className="subhead">{t.common.guardians}</div>
        {child.guardians.length === 0 ? (
          <p className="muted">{t.common.empty}</p>
        ) : (
          child.guardians.map((g) => (
            <div key={g.guardian_user_id} style={{ marginBottom: 8 }}>
              <b>{g.full_name}</b>{" "}
              <span className="muted">({g.relationship_type})</span>
            </div>
          ))
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 24 }}>
          <button
            type="button"
            className="btn"
            style={{ flex: 1 }}
            onClick={() => {
              modal.close();
              openEditChild(child);
            }}
          >
            {t.common.edit}
          </button>
          <button
            type="button"
            className="btn-ghost btn"
            style={{ flex: 1 }}
            onClick={() => {
              modal.close();
              openTransfer(child);
            }}
          >
            {t.children.transferGroup}
          </button>
        </div>
        {child.is_active && (
          <button
            type="button"
            className="btn--quiet btn"
            style={{
              width: "100%",
              marginTop: 8,
              color: "var(--neg)",
              justifyContent: "center",
            }}
            onClick={async () => {
              const ok = await confirm({
                title: t.common.deactivateTitle,
                body: t.children.deactivateBody,
                confirmLabel: t.common.deactivate,
                cancelLabel: t.common.cancel,
                danger: true,
              });
              if (!ok) return;
              await api.updateChild(child.id, { is_active: false });
              modal.close();
              toast.show(t.common.saved);
              load();
            }}
          >
            {t.common.deactivate}
          </button>
        )}
      </div>,
      { title: child.full_name, size: "default" },
    );
  }

  function openAddChild(): void {
    openChildForm(null);
  }

  function openEditChild(child: Child): void {
    openChildForm(child);
  }

  function openChildForm(existing: Child | null): void {
    let fullName = existing?.full_name ?? "";
    let birthDate = existing?.birth_date ?? "";
    let gender = existing?.gender ?? "";
    let medicalNotes = existing?.medical_notes ?? "";
    let groupId = groups[0]?.id ?? "";
    let startDate = isoDate(new Date());
    let discountType: DiscountType = "NONE";
    let discountPercent = "";
    let guardianName = "";
    let guardianPhone = "";
    let relation = "MOTHER";
    let saving = false;
    let error = "";

    function render(): void {
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            error = "";
            saving = true;
            render();
            try {
              if (existing) {
                await api.updateChild(existing.id, {
                  full_name: fullName,
                  birth_date: birthDate,
                  gender: gender || null,
                  medical_notes: medicalNotes || null,
                });
              } else {
                const created = await api.createChild({
                  full_name: fullName,
                  birth_date: birthDate,
                  gender: gender || undefined,
                  medical_notes: medicalNotes || undefined,
                });
                if (groupId) {
                  await api.createEnrollment(created.id, {
                    branch_id: branchId,
                    group_id: groupId,
                    start_date: startDate,
                    status: "ACTIVE",
                    discount_type:
                      discountType !== "NONE" ? discountType : undefined,
                    discount_percent: discountPercent || undefined,
                  });
                }
                if (guardianName && guardianPhone) {
                  await api.addGuardian(created.id, {
                    full_name: guardianName,
                    phone: guardianPhone,
                    relationship_type: relation,
                    is_primary: true,
                  });
                }
              }
              modal.close();
              toast.show(t.children.savedChild);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-sec">{t.children.aboutChild}</div>
          <div className="form-grid">
            <div className="field">
              <label>
                {t.common.fullName}
                <span className="req">*</span>
              </label>
              <input
                className="input"
                defaultValue={fullName}
                required
                onChange={(e) => (fullName = e.target.value)}
              />
            </div>
            <div className="field">
              <label>
                {t.common.birthDate}
                <span className="req">*</span>
              </label>
              <input
                className="input"
                type="date"
                defaultValue={birthDate}
                required
                onChange={(e) => (birthDate = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.children.gender}</label>
              <select
                className="input"
                defaultValue={gender}
                onChange={(e) => (gender = e.target.value)}
              >
                <option value="">—</option>
                <option value="MALE">{t.children.boy}</option>
                <option value="FEMALE">{t.children.girl}</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label>{t.children.medicalNotes}</label>
            <textarea
              className="input"
              defaultValue={medicalNotes}
              placeholder={t.children.medicalHint}
              onChange={(e) => (medicalNotes = e.target.value)}
            />
          </div>

          {!existing && (
            <>
              <div className="form-sec">{t.children.group}</div>
              <div className="form-grid">
                <div className="field">
                  <label>{t.children.group}</label>
                  <select
                    className="input"
                    defaultValue={groupId}
                    onChange={(e) => (groupId = e.target.value)}
                  >
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>{t.children.startDate}</label>
                  <input
                    className="input"
                    type="date"
                    defaultValue={startDate}
                    onChange={(e) => (startDate = e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>{t.children.discount}</label>
                  <select
                    className="input"
                    defaultValue={discountType}
                    onChange={(e) =>
                      (discountType = e.target.value as DiscountType)
                    }
                  >
                    <option value="NONE">{t.children.discountNone}</option>
                    <option value="SIBLING">
                      {t.children.discountSibling}
                    </option>
                    <option value="STAFF_CHILD">
                      {t.children.discountStaffChild}
                    </option>
                    <option value="SOCIAL">{t.children.discountSocial}</option>
                    <option value="OTHER">{t.children.discountOther}</option>
                  </select>
                </div>
                <div className="field">
                  <label>{t.children.discountPercent}</label>
                  <input
                    className="input"
                    inputMode="decimal"
                    defaultValue={discountPercent}
                    onChange={(e) => (discountPercent = e.target.value)}
                  />
                </div>
              </div>

              <div className="form-sec">
                {t.children.guardianSection} ({t.common.optional})
              </div>
              <div className="form-grid">
                <div className="field">
                  <label>{t.common.fullName}</label>
                  <input
                    className="input"
                    onChange={(e) => (guardianName = e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>{t.common.phone}</label>
                  <input
                    className="input"
                    placeholder="+998901234567"
                    onChange={(e) => (guardianPhone = e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>{t.children.relation}</label>
                  <select
                    className="input"
                    defaultValue={relation}
                    onChange={(e) => (relation = e.target.value)}
                  >
                    <option value="MOTHER">{t.children.rMother}</option>
                    <option value="FATHER">{t.children.rFather}</option>
                    <option value="RELATIVE">{t.children.rRelative}</option>
                    <option value="OTHER">{t.children.rOther}</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {error && <p className="error">{error}</p>}
          <button
            className="btn"
            type="submit"
            disabled={saving}
            style={{ marginTop: 8 }}
          >
            {saving ? t.common.saving : t.common.save}
          </button>
        </form>,
        {
          title: existing ? t.children.editChild : t.children.addChild,
          size: "wide",
        },
      );
    }

    render();
  }

  function openTransfer(child: Child): void {
    let newGroupId = groups[0]?.id ?? "";
    let effectiveDate = isoDate(new Date());
    let reason = "";
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
              await api.transferChild(child.id, {
                new_group_id: newGroupId,
                effective_date: effectiveDate,
                reason: reason || undefined,
              });
              modal.close();
              toast.show(t.children.transferDone);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <p className="info-box" style={{ marginBottom: 16 }}>
            {t.children.transferHint}
          </p>
          <div className="field">
            <label>{t.children.newGroup}</label>
            <select
              className="input"
              defaultValue={newGroupId}
              onChange={(e) => (newGroupId = e.target.value)}
            >
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>{t.children.effectiveDate}</label>
            <input
              className="input"
              type="date"
              defaultValue={effectiveDate}
              onChange={(e) => (effectiveDate = e.target.value)}
            />
          </div>
          <div className="field">
            <label>
              {t.common.reason} ({t.common.optional})
            </label>
            <input
              className="input"
              onChange={(e) => (reason = e.target.value)}
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button
            className="btn"
            type="submit"
            disabled={saving}
            style={{ marginTop: 8 }}
          >
            {saving ? t.common.saving : t.children.transfer}
          </button>
        </form>,
        {
          title: t.children.transferGroup,
          subtitle: child.full_name,
          size: "narrow",
        },
      );
    }
    render();
  }

  function openImportWizard(): void {
    // 3 bosqichli sehrgar: 1) fayl tanlash → 2) dry-run ko'rib chiqish →
    // 3) tasdiqlab haqiqiy import. Har bosqich bir xil modalda qayta chiziladi.
    let step: 1 | 2 | 3 = 1;
    let file: File | null = null;
    let importGroupId = groups[0]?.id ?? "";
    let preview: ImportResult | null = null;
    let busy = false;
    let error = "";

    async function runImport(dryRun: boolean): Promise<void> {
      if (!file) return;
      busy = true;
      error = "";
      render();
      try {
        const result = await api.importChildren(
          branchId,
          importGroupId,
          dryRun,
          file,
        );
        if (dryRun) {
          preview = result;
          step = 2;
        } else {
          modal.close();
          toast.show(`${result.imported} ${t.children.importDone}`);
          load();
          return;
        }
      } catch (err) {
        error = err instanceof ApiError ? err.message : t.common.errTitle;
      } finally {
        busy = false;
        render();
      }
    }

    function render(): void {
      modal.open(
        <div>
          <div
            className="steps"
            style={{ display: "flex", gap: 8, marginBottom: 16 }}
          >
            {[
              t.children.importUploadStep,
              t.children.importPreviewStep,
              t.children.importConfirmStep,
            ].map((label, i) => (
              <span
                key={label}
                className={`chip${step === i + 1 ? " on" : ""}`}
              >
                {i + 1}. {label}
              </span>
            ))}
          </div>

          {step === 1 && (
            <>
              <div className="field">
                <label>{t.children.importGroup}</label>
                <select
                  className="input"
                  defaultValue={importGroupId}
                  onChange={(e) => (importGroupId = e.target.value)}
                >
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>{t.children.importChooseFile}</label>
                <input
                  className="input"
                  type="file"
                  accept=".xlsx,.xlsm,.csv"
                  onChange={(e) => {
                    file = e.target.files?.[0] ?? null;
                    render();
                  }}
                />
              </div>
              <p className="field__hint">{t.children.importDryRunHint}</p>
              {error && <p className="error">{error}</p>}
              <button
                type="button"
                className="btn"
                disabled={busy || !file || !importGroupId}
                onClick={() => runImport(true)}
                style={{ marginTop: 8 }}
              >
                {busy ? t.common.loading : t.common.next}
              </button>
            </>
          )}

          {step === 2 && preview && (
            <>
              <div
                style={{
                  display: "flex",
                  gap: 16,
                  marginBottom: 16,
                  flexWrap: "wrap",
                }}
              >
                <div className="kpi" style={{ flex: 1, minWidth: 150 }}>
                  <div className="kpi__top">
                    <span className="kpi__label">
                      {t.children.importTotalRows}
                    </span>
                  </div>
                  <div className="kpi__value">{preview.total_rows}</div>
                </div>
                <div className="kpi" style={{ flex: 1, minWidth: 150 }}>
                  <div className="kpi__top">
                    <span className="kpi__label">
                      {t.children.importValidRows}
                    </span>
                  </div>
                  <div className="kpi__value">{preview.valid_rows}</div>
                </div>
              </div>
              <div
                className="tbl-wrap"
                style={{ maxHeight: 320, overflowY: "auto" }}
              >
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>{t.children.importRowNumber}</th>
                      <th>{t.common.fullName}</th>
                      <th>{t.common.birthDate}</th>
                      <th>{t.children.parent}</th>
                      <th>{t.children.importErrors}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r) => (
                      <tr key={r.row_number}>
                        <td>{r.row_number}</td>
                        <td>{r.full_name ?? "—"}</td>
                        <td>{r.birth_date ?? "—"}</td>
                        <td>{r.guardian_name ?? "—"}</td>
                        <td>
                          {r.valid ? (
                            <span className="muted">—</span>
                          ) : (
                            <span style={{ color: "var(--neg)" }}>
                              {r.errors.join("; ")}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {error && <p className="error">{error}</p>}
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button
                  type="button"
                  className="btn-ghost btn"
                  onClick={() => {
                    step = 1;
                    render();
                  }}
                >
                  {t.common.back}
                </button>
                <button
                  type="button"
                  className="btn"
                  style={{ flex: 1 }}
                  disabled={busy || preview.valid_rows === 0}
                  onClick={() => {
                    step = 3;
                    render();
                  }}
                >
                  {t.common.next}
                </button>
              </div>
            </>
          )}

          {step === 3 && preview && (
            <>
              <p className="info-box" style={{ marginBottom: 16 }}>
                {preview.valid_rows} / {preview.total_rows} —{" "}
                {t.children.importValidRows}
              </p>
              {error && <p className="error">{error}</p>}
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className="btn-ghost btn"
                  onClick={() => {
                    step = 2;
                    render();
                  }}
                >
                  {t.common.back}
                </button>
                <button
                  type="button"
                  className="btn"
                  style={{ flex: 1 }}
                  disabled={busy}
                  onClick={() => runImport(false)}
                >
                  {busy ? t.common.saving : t.children.importConfirmButton}
                </button>
              </div>
            </>
          )}
        </div>,
        { title: t.children.importTitle, size: "wide" },
      );
    }
    render();
  }

  return (
    <>
      {!ready ? (
        <div className="card">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div className="sk-row" key={i}>
              <div
                className="sk"
                style={{ width: 34, height: 34, borderRadius: 10 }}
              />
              <div style={{ flex: 1 }}>
                <div className="sk sk-line" style={{ width: "38%" }} />
                <div className="sk sk-line" style={{ width: "22%" }} />
              </div>
              <div className="sk sk-line" style={{ width: 80 }} />
            </div>
          ))}
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={children}
          rowKey={(c) => c.id}
          searchText={(c) =>
            [
              c.full_name,
              ...c.guardians.map((g) => g.full_name),
              ...c.guardians.map((g) => parentPhones[g.guardian_user_id] ?? ""),
              groups.find((g) => g.id === childGroup[c.id])?.name ?? "",
            ].join(" ")
          }
          searchPlaceholder={t.common.search}
          filters={[
            { key: "all", label: t.common.all },
            { key: "active", label: t.children.filterActive },
            { key: "debt", label: t.children.filterDebt },
            { key: "waiting", label: t.children.filterWaiting },
            { key: "left", label: t.children.filterLeft },
          ]}
          filterFn={(c, f) =>
            f === "debt" ? (childDebt[c.id] ?? 0) > 0 : c.status === f
          }
          onRowClick={openDetail}
          emptyTitle={t.common.nothingFound}
          emptySub={t.common.nothingFoundSub}
          clearFiltersLabel={t.common.clearFilters}
          showingLabel={t.common.showing}
          ofLabel={t.common.of}
          actions={
            <>
              <button
                type="button"
                className="btn-ghost btn btn-sm"
                onClick={openImportWizard}
              >
                <IconUpload size={14} /> {t.children.importTitle}
              </button>
              <button
                type="button"
                className="btn btn-sm"
                onClick={openAddChild}
              >
                <IconUsers size={14} /> {t.children.addChild}
              </button>
            </>
          }
        />
      )}
    </>
  );
}
