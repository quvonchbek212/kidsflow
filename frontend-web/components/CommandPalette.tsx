"use client";

// Ctrl+K tezkor qidiruv/navigatsiya oynasi.

import { useEffect, useRef, useState, type ReactNode } from "react";

export interface CommandItem {
  key: string;
  label: string;
  category: string;
  onSelect: () => void;
}

export function CommandPalette({
  open,
  onClose,
  items,
  placeholder,
  emptyLabel,
}: {
  open: boolean;
  onClose: () => void;
  items: CommandItem[];
  placeholder: string;
  emptyLabel: string;
}): ReactNode {
  const [query, setQuery] = useState("");
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSel(0);
      window.setTimeout(() => inputRef.current?.focus(), 20);
    }
  }, [open]);

  const filtered = items
    .filter((it) => it.label.toLowerCase().includes(query.trim().toLowerCase()))
    .slice(0, 9);

  function run(index: number): void {
    const item = filtered[index];
    if (!item) return;
    onClose();
    window.setTimeout(item.onSelect, 40);
  }

  return (
    <div
      id="cmdk"
      className={open ? "on" : undefined}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="cmdk__box">
        <input
          ref={inputRef}
          className="cmdk__in"
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSel(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
            else if (e.key === "ArrowDown") {
              e.preventDefault();
              setSel((s) => Math.min(s + 1, filtered.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setSel((s) => Math.max(s - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              run(sel);
            }
          }}
        />
        <div className="cmdk__list">
          {filtered.length === 0 ? (
            <div
              style={{
                padding: 24,
                textAlign: "center",
                color: "var(--ink-3)",
                fontSize: 13.5,
              }}
            >
              {emptyLabel}
            </div>
          ) : (
            filtered.map((item, i) => (
              <div
                key={item.key}
                className={`cmdk__item${i === sel ? " sel" : ""}`}
                onMouseEnter={() => setSel(i)}
                onClick={() => run(i)}
              >
                {item.label}
                <span className="cmdk__cat">{item.category}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
