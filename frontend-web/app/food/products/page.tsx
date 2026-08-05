"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { IconPlus } from "@/components/icons";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { ApiError, api, type FoodProduct } from "@/lib/api";
import { money } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function FoodProductsPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user}>
      <ProductsContent />
    </AppShell>
  );
}

function ProductsContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.food.productsTitle, subtitle: t.food.productsSub });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();

  const [products, setProducts] = useState<FoodProduct[]>([]);
  const [ready, setReady] = useState(false);

  function load(): void {
    if (!branchId) return;
    setReady(false);
    api
      .listFoodProducts(branchId)
      .then(setProducts)
      .catch(() => setProducts([]))
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId]);

  const REASONS: [string, string][] = [
    ["PURCHASE", t.food.reasonPurchase],
    ["CONSUMPTION", t.food.reasonConsumption],
    ["ADJUSTMENT", t.food.reasonAdjustment],
    ["WASTE", t.food.reasonWaste],
  ];

  function openProductForm(): void {
    let name = "";
    let unit = "kg";
    let unitCost = "";
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
              await api.createFoodProduct({
                branch_id: branchId,
                name,
                unit,
                unit_cost: unitCost || undefined,
              });
              modal.close();
              toast.show(t.common.saved);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-grid">
            <div className="field span-2">
              <label>
                {t.common.name}
                <span className="req">*</span>
              </label>
              <input className="input" required onChange={(e) => (name = e.target.value)} />
            </div>
            <div className="field">
              <label>
                {t.food.unit}
                <span className="req">*</span>
              </label>
              <input
                className="input"
                defaultValue={unit}
                required
                onChange={(e) => (unit = e.target.value)}
              />
            </div>
            <div className="field">
              <label>
                {t.food.unitCost} ({t.common.sum})
              </label>
              <input
                className="input"
                inputMode="decimal"
                onChange={(e) => (unitCost = e.target.value)}
              />
            </div>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={saving}>
            {saving ? t.common.saving : t.common.save}
          </button>
        </form>,
        { title: t.food.addProduct, size: "default" },
      );
    }
    render();
  }

  function openMovementForm(product: FoodProduct): void {
    let movementType: "IN" | "OUT" = "IN";
    let quantity = "";
    let reason = "PURCHASE";
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
              await api.recordStockMovement({
                product_id: product.id,
                movement_type: movementType,
                quantity,
                reason,
              });
              modal.close();
              toast.show(t.common.saved);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-grid">
            <div className="field">
              <label>{t.food.stockMovement}</label>
              <select
                className="input"
                defaultValue={movementType}
                onChange={(e) => (movementType = e.target.value as "IN" | "OUT")}
              >
                <option value="IN">{t.food.movementIn}</option>
                <option value="OUT">{t.food.movementOut}</option>
              </select>
            </div>
            <div className="field">
              <label>
                {t.food.quantity} ({product.unit})<span className="req">*</span>
              </label>
              <input
                className="input"
                inputMode="decimal"
                required
                onChange={(e) => (quantity = e.target.value)}
              />
            </div>
            <div className="field span-2">
              <label>{t.food.reason}</label>
              <select className="input" defaultValue={reason} onChange={(e) => (reason = e.target.value)}>
                {REASONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={saving}>
            {saving ? t.common.saving : t.common.save}
          </button>
        </form>,
        { title: t.food.stockMovement, subtitle: product.name, size: "default" },
      );
    }
    render();
  }

  return (
    <>

      <div className="card">
        <div className="card__head">
          <div>
            <h3>{t.food.productsTitle}</h3>
          </div>
          <button type="button" className="btn btn-sm" onClick={openProductForm}>
            <IconPlus size={14} /> {t.food.addProduct}
          </button>
        </div>
        {!ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : products.length === 0 ? (
          <div className="panel-empty">{t.common.empty}</div>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.common.name}</th>
                  <th>{t.food.unit}</th>
                  <th className="r">{t.food.stock}</th>
                  <th className="r">{t.food.unitCost}</th>
                  <th className="r" />
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <b>{p.name}</b>
                    </td>
                    <td style={{ color: "var(--ink-2)" }}>{p.unit}</td>
                    <td className="r num" style={{ fontWeight: 600 }}>
                      {p.current_stock}
                    </td>
                    <td className="r num" style={{ color: "var(--ink-2)" }}>
                      {p.unit_cost ? money(p.unit_cost) : "—"}
                    </td>
                    <td className="r">
                      <button
                        type="button"
                        className="btn-ghost btn btn-sm"
                        onClick={() => openMovementForm(p)}
                      >
                        {t.food.stockMovement}
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
