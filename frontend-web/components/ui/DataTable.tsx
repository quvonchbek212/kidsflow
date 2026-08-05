"use client";

// Generik jadval: qidiruv, ixtiyoriy chip-filtr, ustun bo'yicha saralash,
// sahifalash. Bolalar/Xodimlar/Xarajatlar/To'lovlar jadvallarida ishlatiladi.

import { useMemo, useState, type ReactNode } from "react";

import { IconChevronLeft, IconChevronRight, IconEmpty, IconSearch, IconX } from "@/components/icons";

/** Sahifa raqamlari; ko'p sahifa bo'lsa o'rtasi `null` (…) bilan qisqaradi. */
function pageButtons(current: number, total: number): (number | null)[] {
  const out: (number | null)[] = [];
  for (let p = 1; p <= total; p++) {
    if (total > 7 && p > 2 && p < total - 1 && Math.abs(p - current) > 1) {
      if (out[out.length - 1] !== null) out.push(null);
      continue;
    }
    out.push(p);
  }
  return out;
}

export interface DataTableColumn<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
  align?: "left" | "right" | "center";
}

export interface DataTableFilter {
  key: string;
  label: string;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  searchText?: (row: T) => string;
  searchPlaceholder: string;
  filters?: DataTableFilter[];
  filterFn?: (row: T, filterKey: string) => boolean;
  onRowClick?: (row: T) => void;
  pageSize?: number;
  emptyTitle: string;
  emptySub: string;
  clearFiltersLabel: string;
  showingLabel: string;
  ofLabel: string;
  actions?: ReactNode;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  searchText,
  searchPlaceholder,
  filters,
  filterFn,
  onRowClick,
  pageSize = 10,
  emptyTitle,
  emptySub,
  clearFiltersLabel,
  showingLabel,
  ofLabel,
  actions,
}: DataTableProps<T>): ReactNode {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<1 | -1>(1);
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    let result = rows;
    if (filter !== "all" && filterFn) result = result.filter((r) => filterFn(r, filter));
    if (query.trim() && searchText) {
      const q = query.trim().toLowerCase();
      result = result.filter((r) => searchText(r).toLowerCase().includes(q));
    }
    if (sortKey) {
      const col = columns.find((c) => c.key === sortKey);
      if (col?.sortValue) {
        result = [...result].sort((a, b) => {
          const x = col.sortValue!(a);
          const y = col.sortValue!(b);
          if (typeof x === "number" && typeof y === "number") return (x - y) * sortDir;
          return String(x).localeCompare(String(y)) * sortDir;
        });
      }
    }
    return result;
  }, [rows, filter, filterFn, query, searchText, sortKey, sortDir, columns]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const from = (safePage - 1) * pageSize;
  const pageRows = filtered.slice(from, from + pageSize);

  function toggleSort(key: string): void {
    if (sortKey === key) {
      setSortDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setSortDir(1);
    }
  }

  function resetFilters(): void {
    setQuery("");
    setFilter("all");
    setPage(1);
  }

  return (
    <div className="card" style={{ padding: 0 }}>
      <div className="toolbar">
        {searchText && (
          <div className={`search${query ? " has" : ""}`}>
            <IconSearch size={15} />
            <input
              className="input"
              placeholder={searchPlaceholder}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
            />
            {query && (
              <button
                type="button"
                className="search__clear"
                onClick={() => setQuery("")}
                aria-label="Tozalash"
              >
                <IconX size={14} />
              </button>
            )}
          </div>
        )}
        {filters?.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`chip${filter === f.key ? " on" : ""}`}
            onClick={() => {
              setFilter(f.key);
              setPage(1);
            }}
          >
            {f.label}
          </button>
        ))}
        {actions && <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>{actions}</div>}
      </div>

      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              {columns.map((c) => {
                const align = c.align === "right" ? "r" : c.align === "center" ? "c" : "";
                const sorted = sortKey === c.key;
                return (
                  <th
                    key={c.key}
                    className={`${align}${sorted ? " sorted" : ""}`.trim() || undefined}
                    data-sort={c.sortValue ? "" : undefined}
                    onClick={c.sortValue ? () => toggleSort(c.key) : undefined}
                  >
                    {c.label}
                    {/* Strelka doim chiziladi (ko'rinishi CSS'da) — shunda
                        saralashda ustun eni sakramaydi. */}
                    {c.sortValue && <span className="arrow">{sorted && sortDir === -1 ? "▼" : "▲"}</span>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: 0 }}>
                  <div className="state">
                    <div className="state__ico">
                      <IconEmpty size={24} />
                    </div>
                    <h4>{emptyTitle}</h4>
                    <p>{emptySub}</p>
                    {(query || filter !== "all") && (
                      <button type="button" className="btn-ghost btn" onClick={resetFilters}>
                        {clearFiltersLabel}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              pageRows.map((row) => (
                <tr
                  key={rowKey(row)}
                  className={onRowClick ? "clickable" : undefined}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      className={c.align === "right" ? "r" : c.align === "center" ? "c" : undefined}
                    >
                      {c.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {filtered.length > 0 &&
        (totalPages > 1 ? (
          <div className="pager">
            <span className="pager__info">
              {showingLabel} {from + 1}–{Math.min(from + pageSize, filtered.length)} {ofLabel}{" "}
              {filtered.length}
            </span>
            <button
              type="button"
              className="pager__btn"
              disabled={safePage === 1}
              onClick={() => setPage(safePage - 1)}
              aria-label="Oldingi"
            >
              <IconChevronLeft size={14} />
            </button>
            {pageButtons(safePage, totalPages).map((p, i) =>
              p === null ? (
                <span key={`gap-${i}`} style={{ color: "var(--ink-3)", padding: "0 2px" }}>
                  …
                </span>
              ) : (
                <button
                  key={p}
                  type="button"
                  className={`pager__btn${p === safePage ? " on" : ""}`}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              ),
            )}
            <button
              type="button"
              className="pager__btn"
              disabled={safePage === totalPages}
              onClick={() => setPage(safePage + 1)}
              aria-label="Keyingi"
            >
              <IconChevronRight size={14} />
            </button>
          </div>
        ) : (
          <div className="pager">
            <span className="pager__info">
              {showingLabel} {filtered.length} {ofLabel} {rows.length}
            </span>
          </div>
        ))}
    </div>
  );
}
