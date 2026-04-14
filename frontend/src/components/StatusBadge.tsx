import clsx from "clsx";

const STATUS_TEXT: Record<string, string> = {
  pending: "等待",
  running: "运行中",
  done: "完成",
  failed: "失败",
};

const STATUS_CLASS: Record<string, string> = {
  pending: "border-amber-700/60 bg-amber-950/40 text-amber-300",
  running: "border-lime-700/60 bg-lime-950/40 text-lime-300",
  done: "border-emerald-700/60 bg-emerald-950/40 text-emerald-300",
  failed: "border-red-800/70 bg-red-950/50 text-red-300",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex min-w-16 items-center justify-center rounded border px-2 py-1 text-xs",
        STATUS_CLASS[status] || "border-line bg-[#191b16] text-stone-300",
      )}
    >
      {STATUS_TEXT[status] || status}
    </span>
  );
}
