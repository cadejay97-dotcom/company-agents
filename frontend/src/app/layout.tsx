import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "生产飞轮",
  description: "一人和多 Agent 的执行控制台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="bg-ink text-stone-100 antialiased">{children}</body>
    </html>
  );
}
