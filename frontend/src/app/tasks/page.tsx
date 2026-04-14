"use client";

import { useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";
import { TaskList } from "@/components/TaskList";
import type { Task } from "@/lib/types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadTasks() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/tasks", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "任务读取失败");
        return;
      }
      setTasks(data.tasks || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务读取失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTasks();
  }, []);

  return (
    <div className="min-h-screen bg-ink text-stone-100">
      <NavBar />
      <main className="mx-auto max-w-7xl px-5 py-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm text-leaf">Tasks</p>
            <h1 className="mt-2 text-3xl font-semibold text-stone-50">
              任务历史
            </h1>
          </div>
          <button
            type="button"
            onClick={loadTasks}
            className="rounded border border-line px-4 py-2 text-sm text-stone-300 transition hover:border-stone-500 hover:text-stone-50"
          >
            刷新
          </button>
        </div>

        {loading ? <p className="text-stone-500">读取任务中</p> : null}
        {error ? (
          <div className="rounded border border-red-800 bg-red-950/40 px-4 py-3 text-red-200">
            {error}
          </div>
        ) : null}
        {!loading && !error ? <TaskList tasks={tasks} /> : null}
      </main>
    </div>
  );
}
