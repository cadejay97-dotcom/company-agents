"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "登录失败");
        return;
      }
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-ink px-5">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded border border-line bg-panel p-6"
      >
        <p className="text-sm text-leaf">公司智能体</p>
        <h1 className="mt-2 text-2xl font-semibold text-stone-50">进入生产飞轮</h1>
        <p className="mt-3 text-sm leading-6 text-stone-400">
          输入访问密码，打开你的 Agent 控制台。
        </p>

        <label className="mt-6 block text-sm text-stone-300" htmlFor="password">
          访问密码
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-2 w-full rounded border border-line bg-ink px-3 py-2 text-stone-100 outline-none transition focus:border-leaf"
          autoComplete="current-password"
        />

        {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full rounded bg-leaf px-4 py-2 font-medium text-[#091008] transition hover:bg-[#91c27b] disabled:cursor-wait disabled:opacity-60"
        >
          {loading ? "验证中" : "登录"}
        </button>
      </form>
    </main>
  );
}
