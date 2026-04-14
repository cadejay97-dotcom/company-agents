"use client";

import { useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabase";

interface Chunk {
  id: number;
  chunk_type: string;
  content: Record<string, unknown>;
  created_at: string;
}

type DisplayItem =
  | { type: "event"; key: string; chunk: Chunk }
  | { type: "text"; key: string; text: string };

function textValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function buildDisplayItems(chunks: Chunk[]): DisplayItem[] {
  const items: DisplayItem[] = [];

  for (const chunk of chunks) {
    if (chunk.chunk_type !== "chunk") {
      items.push({ type: "event", key: `event-${chunk.id}`, chunk });
      continue;
    }

    const text = textValue(chunk.content?.text);
    if (!text) continue;

    const previous = items[items.length - 1];
    if (previous?.type === "text") {
      previous.text += text;
    } else {
      items.push({ type: "text", key: `text-${chunk.id}`, text });
    }
  }

  return items;
}

function renderChunk(chunk: Chunk) {
  const content = chunk.content || {};
  switch (chunk.chunk_type) {
    case "start":
      return <span className="text-stone-500">任务开始</span>;
    case "chunk":
      return <span className="text-stone-100">{textValue(content.text)}</span>;
    case "tool":
      return (
        <span className="text-amber-300">
          [工具调用] {textValue(content.name)}
          {content.result ? ` ${String(content.result).slice(0, 180)}` : ""}
        </span>
      );
    case "done": {
      const verdict = textValue(content.verdict);
      if (verdict === "pass") {
        return (
          <span className="font-semibold text-emerald-400">
            ✓ VERDICT: PASS · 完成
          </span>
        );
      }
      if (verdict === "fail") {
        return (
          <span className="font-semibold text-red-400">
            ✗ VERDICT: FAIL · 下游任务已阻断
          </span>
        );
      }
      return <span className="text-emerald-300">完成</span>;
    }
    case "error":
      return (
        <span className="text-red-300">
          错误: {textValue(content.message) || JSON.stringify(content)}
        </span>
      );
    default:
      return <span className="text-stone-400">{JSON.stringify(content)}</span>;
  }
}

export function Terminal({ taskId }: { taskId: string }) {
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loadError, setLoadError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const displayItems = buildDisplayItems(chunks);

  useEffect(() => {
    let alive = true;

    supabase
      .from("task_chunks")
      .select("*")
      .eq("task_id", taskId)
      .order("id")
      .then(({ data, error }) => {
        if (!alive) return;
        if (error) {
          setLoadError(error.message);
          return;
        }
        if (data) setChunks(data as Chunk[]);
      });

    const channel = supabase
      .channel(`task_chunks:${taskId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "task_chunks",
          filter: `task_id=eq.${taskId}`,
        },
        (payload) => {
          setChunks((prev) => [...prev, payload.new as Chunk]);
        },
      )
      .subscribe();

    return () => {
      alive = false;
      supabase.removeChannel(channel);
    };
  }, [taskId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chunks]);

  return (
    <section className="rounded border border-line bg-black">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <span className="font-mono text-xs uppercase tracking-wide text-stone-500">
          task_chunks/{taskId}
        </span>
        <span className="text-xs text-stone-500">{chunks.length} chunks</span>
      </div>
      <div className="h-[34rem] overflow-y-auto p-4 font-mono text-sm leading-7">
        {loadError ? (
          <div className="text-red-300">读取失败: {loadError}</div>
        ) : null}
        {!chunks.length && !loadError ? (
          <div className="text-stone-600">等待 Agent 输出</div>
        ) : null}
        {displayItems.map((item) => (
          <div key={item.key} className="whitespace-pre-wrap break-words">
            {item.type === "text" ? (
              <span className="text-stone-100">{item.text}</span>
            ) : (
              renderChunk(item.chunk)
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
