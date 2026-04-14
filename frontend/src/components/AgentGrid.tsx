"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { AGENTS_BY_LAYER, type Layer } from "@/lib/agents";

type RunningState = Record<string, boolean>;

const LAYER_STYLE: Record<
  Layer,
  {
    section: string;
    eyebrow: string;
    icon: string;
    card: string;
    desc: string;
  }
> = {
  perception: {
    section: "border-line",
    eyebrow: "text-stone-400",
    icon: "border-line bg-[#181916] text-stone-400",
    card: "border-line bg-panel",
    desc: "text-stone-500",
  },
  judgment: {
    section: "border-leaf/70",
    eyebrow: "text-leaf",
    icon: "border-leaf/70 bg-[#172114] text-leaf shadow-[0_0_24px_rgba(127,176,105,0.16)]",
    card: "border-leaf/70 bg-[#13180f] shadow-[0_0_32px_rgba(127,176,105,0.08)]",
    desc: "text-stone-300",
  },
  generation: {
    section: "border-line",
    eyebrow: "text-stone-300",
    icon: "border-line bg-[#1b1d18] text-leaf",
    card: "border-line bg-panel",
    desc: "text-stone-400",
  },
  validation: {
    section: "border-amber-500/50",
    eyebrow: "text-amber-400",
    icon: "border-amber-500/60 bg-[#211a10] text-amber-300",
    card: "border-amber-500/50 bg-[#17140f]",
    desc: "text-amber-100/70",
  },
  exchange: {
    section: "border-line",
    eyebrow: "text-stone-300",
    icon: "border-line bg-[#1b1d18] text-leaf",
    card: "border-line bg-panel",
    desc: "text-stone-400",
  },
  governance: {
    section: "border-stone-800",
    eyebrow: "text-stone-500",
    icon: "border-stone-800 bg-[#11120f] text-stone-500",
    card: "border-stone-800 bg-[#10110e]",
    desc: "text-stone-500",
  },
};

export function AgentGrid() {
  const router = useRouter();
  const [descriptions, setDescriptions] = useState<Record<string, string>>({});
  const [running, setRunning] = useState<RunningState>({});
  const [error, setError] = useState<string>("");

  async function runAgent(taskType: string, fallbackPrompt: string) {
    const description = (descriptions[taskType] || fallbackPrompt).trim();
    if (!description) {
      setError("请输入任务描述");
      return;
    }

    setError("");
    setRunning((prev) => ({ ...prev, [taskType]: true }));
    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_type: taskType, description }),
      });
      const data = await response.json();
      if (!response.ok || data.error) {
        setError(data.error || "任务启动失败");
        return;
      }
      router.push(`/tasks/${data.task_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务启动失败");
    } finally {
      setRunning((prev) => ({ ...prev, [taskType]: false }));
    }
  }

  return (
    <div className="space-y-4">
      {error ? (
        <div className="rounded border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      <div className="space-y-5">
        {AGENTS_BY_LAYER.map((layer) => {
          const style = LAYER_STYLE[layer.id];
          const isJudgment = layer.id === "judgment";
          const gridClass =
            layer.agents.length === 1
              ? "grid gap-4 md:grid-cols-2 xl:grid-cols-3"
              : "grid gap-4 md:grid-cols-2 xl:grid-cols-4";

          return (
            <section
              key={layer.id}
              className={clsx("rounded border bg-[#0e0f0c] p-4", style.section)}
            >
              <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p
                    className={clsx(
                      "font-mono text-xs uppercase tracking-wide",
                      style.eyebrow,
                    )}
                  >
                    {layer.id}
                  </p>
                  <div className="mt-1 flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-stone-50">
                      {layer.label}
                    </h2>
                    {isJudgment ? (
                      <span className="rounded border border-leaf/60 bg-leaf/10 px-2 py-0.5 text-xs font-medium text-leaf">
                        系统中枢
                      </span>
                    ) : null}
                  </div>
                </div>
                <p className={clsx("text-sm", style.desc)}>{layer.desc}</p>
              </div>

              <div className={gridClass}>
                {layer.agents.map((agent) => {
                  const isRunning = running[agent.task_type];
                  return (
                    <article
                      key={agent.task_type}
                      className={clsx(
                        "flex min-h-72 flex-col rounded border p-4 transition hover:border-stone-500/80",
                        style.card,
                        isJudgment && "md:col-span-2",
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <span
                          className={clsx(
                            "flex h-10 w-10 shrink-0 items-center justify-center rounded border font-mono text-xs",
                            style.icon,
                          )}
                        >
                          {agent.icon}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="font-semibold text-stone-50">
                              {agent.name}
                            </h3>
                            {agent.isGate ? (
                              <span className="rounded border border-amber-500/60 bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wide text-amber-300">
                                GATE
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-1 text-sm leading-6 text-stone-400">
                            {agent.desc}
                          </p>
                        </div>
                      </div>

                      <textarea
                        value={descriptions[agent.task_type] ?? agent.prompt}
                        onChange={(event) =>
                          setDescriptions((prev) => ({
                            ...prev,
                            [agent.task_type]: event.target.value,
                          }))
                        }
                        className="mt-4 min-h-28 flex-1 resize-none rounded border border-line bg-ink px-3 py-2 text-sm leading-6 text-stone-100 outline-none transition placeholder:text-stone-600 focus:border-leaf"
                      />

                      <button
                        type="button"
                        disabled={isRunning}
                        onClick={() => runAgent(agent.task_type, agent.prompt)}
                        className="mt-4 rounded bg-leaf px-4 py-2 text-sm font-medium text-[#091008] transition hover:bg-[#91c27b] disabled:cursor-wait disabled:opacity-60"
                      >
                        {isRunning ? "启动中" : "运行"}
                      </button>
                    </article>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
