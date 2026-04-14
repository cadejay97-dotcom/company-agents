import Link from "next/link";
import { NavBar } from "@/components/NavBar";
import { Terminal } from "@/components/Terminal";

export default async function TaskDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="min-h-screen bg-ink text-stone-100">
      <NavBar />
      <main className="mx-auto max-w-5xl px-5 py-8">
        <Link href="/tasks" className="text-sm text-stone-500 hover:text-stone-200">
          返回任务历史
        </Link>
        <div className="mb-5 mt-4">
          <p className="text-sm text-leaf">Realtime Terminal</p>
          <h1 className="mt-2 text-2xl font-semibold text-stone-50">
            任务 #{id}
          </h1>
        </div>
        <Terminal taskId={id} />
      </main>
    </div>
  );
}
