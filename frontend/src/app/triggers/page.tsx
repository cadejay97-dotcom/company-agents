"use client";

import { useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";
import type { TriggerSchedule, TriggerWebhook } from "@/lib/types";

export default function TriggersPage() {
  const [schedules, setSchedules] = useState<TriggerSchedule[]>([]);
  const [webhooks, setWebhooks] = useState<TriggerWebhook[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTriggers() {
      try {
        const response = await fetch("/api/triggers", { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) {
          setError(data.error || "触发器读取失败");
          return;
        }
        setSchedules(data.schedules || []);
        setWebhooks(data.webhooks || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "触发器读取失败");
      } finally {
        setLoading(false);
      }
    }

    loadTriggers();
  }, []);

  return (
    <div className="min-h-screen bg-ink text-stone-100">
      <NavBar />
      <main className="mx-auto max-w-7xl px-5 py-8">
        <div className="mb-8 max-w-3xl">
          <p className="text-sm text-leaf">Triggers</p>
          <h1 className="mt-2 text-3xl font-semibold text-stone-50">触发器</h1>
          <p className="mt-3 text-base leading-7 text-stone-400">
            当前触发规则来自后端 `triggers.yaml`，这里只读展示。
          </p>
        </div>

        {loading ? <p className="text-stone-500">读取触发器中</p> : null}
        {error ? (
          <div className="rounded border border-red-800 bg-red-950/40 px-4 py-3 text-red-200">
            {error}
          </div>
        ) : null}

        {!loading && !error ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded border border-line bg-panel">
              <div className="border-b border-line px-5 py-4">
                <h2 className="font-semibold text-stone-50">Schedules</h2>
              </div>
              <div className="divide-y divide-line">
                {schedules.map((item, index) => (
                  <div key={`${item.name}-${index}`} className="p-5">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-medium text-stone-100">{item.name}</h3>
                      <code className="rounded bg-ink px-2 py-1 text-xs text-amber-300">
                        {item.cron}
                      </code>
                    </div>
                    <p className="mt-3 text-sm text-stone-400">{item.description}</p>
                    <p className="mt-3 font-mono text-xs text-stone-500">
                      {item.task_type}
                    </p>
                  </div>
                ))}
                {!schedules.length ? (
                  <div className="p-5 text-sm text-stone-500">没有定时触发器</div>
                ) : null}
              </div>
            </section>

            <section className="rounded border border-line bg-panel">
              <div className="border-b border-line px-5 py-4">
                <h2 className="font-semibold text-stone-50">Webhooks</h2>
              </div>
              <div className="divide-y divide-line">
                {webhooks.map((item, index) => (
                  <div key={`${item.path}-${index}`} className="p-5">
                    <h3 className="font-medium text-stone-100">{item.name}</h3>
                    <code className="mt-3 block rounded bg-ink px-3 py-2 text-sm text-leaf">
                      POST {item.path}
                    </code>
                    <p className="mt-3 font-mono text-xs text-stone-500">
                      {item.task_type}
                    </p>
                  </div>
                ))}
                {!webhooks.length ? (
                  <div className="p-5 text-sm text-stone-500">没有事件触发器</div>
                ) : null}
              </div>
            </section>
          </div>
        ) : null}
      </main>
    </div>
  );
}
