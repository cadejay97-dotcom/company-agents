"use client";

import Link from "next/link";
import { AGENT_BY_TYPE } from "@/lib/agents";
import type { Task } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

function formatDate(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TaskList({ tasks }: { tasks: Task[] }) {
  if (!tasks.length) {
    return (
      <div className="rounded border border-line bg-panel px-5 py-12 text-center text-stone-500">
        还没有任务
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded border border-line bg-panel">
      <div className="grid grid-cols-[7rem_8rem_1fr_6rem_8rem] gap-3 border-b border-line px-4 py-3 text-xs uppercase tracking-wide text-stone-500">
        <span>ID</span>
        <span>Agent</span>
        <span>任务</span>
        <span>状态</span>
        <span>创建时间</span>
      </div>
      {tasks.map((task) => {
        const agent = AGENT_BY_TYPE[task.type as keyof typeof AGENT_BY_TYPE];
        return (
          <Link
            key={task.id}
            href={`/tasks/${task.id}`}
            className="grid grid-cols-[7rem_8rem_1fr_6rem_8rem] gap-3 border-b border-line px-4 py-3 text-sm transition last:border-b-0 hover:bg-[#191b16]"
          >
            <span className="font-mono text-stone-400">#{task.id}</span>
            <span className="text-stone-300">{agent?.name || task.type}</span>
            <span className="truncate text-stone-200">{task.description}</span>
            <StatusBadge status={task.status} />
            <span className="text-stone-500">{formatDate(task.created_at)}</span>
          </Link>
        );
      })}
    </div>
  );
}
