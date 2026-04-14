"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AGENTS } from "@/lib/agents";

type RunningState = Record<string, boolean>;

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

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {AGENTS.map((agent) => {
          const isRunning = running[agent.task_type];
          return (
            <article
              key={agent.task_type}
              className="flex min-h-72 flex-col rounded border border-line bg-panel p-4"
            >
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-line bg-[#1b1d18] font-mono text-xs text-leaf">
                  {agent.icon}
                </span>
                <div>
                  <h2 className="font-semibold text-stone-50">{agent.name}</h2>
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
    </div>
  );
}
