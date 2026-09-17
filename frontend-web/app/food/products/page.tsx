"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { useAppUI } from "@/components/AppShell";
import { IconPlus } from "@/components/icons";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError, api, type FoodProduct } from "@/lib/api";
import { money } from "@/lib/format";

export default function FoodProductsPage(): ReactNode {
  return <ProductsContent />;
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
            <label className="field span-2">
              <span className="field__label">
                {t.common.name}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                required
                onChange={(e) => (name = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">
                {t.food.unit}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                defaultValue={unit}
                required
                onChange={(e) => (unit = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">
                {t.food.unitCost} ({t.common.sum})
              </span>
              <input
                className="input"
                inputMode="decimal"
                onChange={(e) => (unitCost = e.target.value)}
              />
            </label>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.save}
            </button>
          </div>
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
            <label className="field">
              <span className="field__label">{t.food.stockMovement}</span>
              <select
                className="input"
                defaultValue={movementType}
                onChange={(e) =>
                  (movementType = e.target.value as "IN" | "OUT")
                }
              >
                <option value="IN">{t.food.movementIn}</option>
                <option value="OUT">{t.food.movementOut}</option>
              </select>
            </label>
            <label className="field">
              <span className="field__label">
                {t.food.quantity} ({product.unit})<span className="req">*</span>
              </span>
              <input
                className="input"
                inputMode="decimal"
                required
                onChange={(e) => (quantity = e.target.value)}
              />
            </label>
            <label className="field span-2">
              <span className="field__label">{t.food.reason}</span>
              <select
                className="input"
                defaultValue={reason}
                onChange={(e) => (reason = e.target.value)}
              >
                {REASONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.save}
            </button>
          </div>
        </form>,
        {
          title: t.food.stockMovement,
          subtitle: product.name,
          size: "default",
        },
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
          <button
            type="button"
            className="btn btn-sm"
            onClick={openProductForm}
          >
            <IconPlus size={14} /> {t.food.addProduct}
          </button>
        </div>
        {!ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : products.length === 0 ? (
          <EmptyState title={t.common.empty} />
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
