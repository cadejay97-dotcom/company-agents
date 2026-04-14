"use client";

import { useEffect, useState } from "react";

interface StateSnapshot {
  current_goal?: string;
  phase?: string;
  constraints?: string[];
  blockers?: string[];
  error?: string;
}

function ListLine({
  label,
  items,
  emptyText,
  tone = "muted",
}: {
  label: string;
  items?: string[];
  emptyText: string;
  tone?: "muted" | "danger";
}) {
  const visibleItems = items?.length ? items : [emptyText];
  const isEmpty = !items?.length;

  return (
    <div className="min-w-0">
      <p className="font-mono text-[11px] uppercase tracking-wide text-stone-600">
        {label}
      </p>
      <ul className="mt-2 flex flex-wrap gap-2">
        {visibleItems.map((item, index) => (
          <li
            key={`${item}-${index}`}
            className={
              tone === "danger" && !isEmpty
                ? "rounded border border-red-800/70 bg-red-950/40 px-2 py-1 text-xs text-red-200"
                : "rounded border border-line bg-ink px-2 py-1 text-xs text-stone-400"
            }
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StatePanel() {
  const [state, setState] = useState<StateSnapshot | null>(null);

  useEffect(() => {
    let alive = true;

    async function loadState() {
      try {
        const response = await fetch("/api/state", { cache: "no-store" });
        const data = (await response.json()) as StateSnapshot;
        if (!alive) return;
        if (!response.ok || data.error) return;
        setState(data);
      } catch {
        if (alive) setState(null);
      }
    }

    loadState();
    return () => {
      alive = false;
    };
  }, []);

  if (!state) return null;

  return (
    <section className="mb-6 rounded border border-line bg-panel px-4 py-4">
      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-wide text-leaf">
            STATE.json
          </p>
          <h2 className="mt-2 break-words text-lg font-semibold leading-7 text-stone-50">
            {state.current_goal || "当前目标未定义"}
          </h2>
        </div>

        <div className="rounded border border-line bg-ink px-3 py-3">
          <p className="font-mono text-[11px] uppercase tracking-wide text-stone-600">
            Phase
          </p>
          <p className="mt-2 break-words font-mono text-sm text-amber-300">
            {state.phase || "unknown"}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <ListLine
          label="Constraints"
          items={state.constraints}
          emptyText="暂无约束"
        />
        <ListLine
          label="Blockers"
          items={state.blockers}
          emptyText="无阻塞"
          tone="danger"
        />
      </div>
    </section>
  );
}
