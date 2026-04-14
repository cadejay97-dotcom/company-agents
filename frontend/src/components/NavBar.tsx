"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "控制台" },
  { href: "/tasks", label: "任务历史" },
  { href: "/triggers", label: "触发器" },
];

export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  return (
    <nav className="border-b border-line bg-panel">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-5">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="font-semibold text-stone-50">
            生产飞轮
          </Link>
          <div className="flex items-center gap-1">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "rounded px-3 py-2 text-sm transition",
                  pathname.startsWith(item.href)
                    ? "bg-[#1e211a] text-stone-50"
                    : "text-stone-400 hover:bg-[#191b16] hover:text-stone-100",
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <button
          type="button"
          onClick={logout}
          className="rounded border border-line px-3 py-1.5 text-sm text-stone-300 transition hover:border-stone-500 hover:text-stone-50"
        >
          退出
        </button>
      </div>
    </nav>
  );
}
