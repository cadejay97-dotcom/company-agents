import { AgentGrid } from "@/components/AgentGrid";
import { NavBar } from "@/components/NavBar";
import { StatePanel } from "@/components/StatePanel";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-ink text-stone-100">
      <NavBar />
      <main className="mx-auto max-w-7xl px-5 py-8">
        <div className="mb-8 max-w-3xl">
          <p className="text-sm text-leaf">Dashboard</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-50">
            生产飞轮
          </h1>
          <p className="mt-3 text-base leading-7 text-stone-400">
            选择 Agent，填入意图，系统会创建任务、写入队列，并把过程输出同步到实时终端。
          </p>
        </div>
        <StatePanel />
        <AgentGrid />
      </main>
    </div>
  );
}
