# Codex Round 2 执行方案：Webhook 修复 + Next.js 前端

## 交接背景

Round 1 已完成 Trigger Layer（scheduler + webhook 动态路由）。
Round 2 目标：修复 2 个已知问题 + 完整重写前端 → 产出一个**可分享、可点开的稳定 URL**。

---

## 现有代码结构（不要改动，除非下面明确要求）

```
company-agents/
├── agents/
│   ├── base.py              # BaseAgent — 不动
│   └── all_agents.py        # 8 个 Agent — 不动
├── core/
│   ├── database.py          # Supabase 单例 — 不动
│   ├── orchestrator.py      # run_task(stream_to_db=True) — 不动
│   ├── scheduler.py         # APScheduler — 不动
│   └── task_queue.py        # push/pop/start/complete/fail — 不动
├── web/
│   ├── app.py               # FastAPI 后端 — 需要小改（加 /api/triggers）
│   └── webhooks.py          # 需要改（换掉 Basic Auth，改 HMAC）
├── triggers.yaml            # 不动
├── supabase_schema.sql      # 不动
├── requirements.txt         # 需要小改（加 hmac 是标准库，不用加）
├── render.yaml              # 不动
├── vercel.json              # 需要改（指向 Next.js 构建输出）
└── frontend/                # 整个目录替换为 Next.js 项目
    └── index.html           # 废弃，删除
```

---

## 任务 1：修复 Webhook 认证

### 问题

`web/webhooks.py` 当前依赖 FastAPI 的 `Depends(require_auth)`（HTTPBasic），
外部平台（GitHub、Feishu、Notion）无法发送 Basic Auth 头，webhook 全部 401。

### 方案

每个 webhook 路由支持两种认证模式（优先级从高到低）：

1. **HMAC-SHA256 签名**（GitHub 风格）：读请求头 `X-Webhook-Signature`，格式 `sha256=<hex>`
2. **Shared Secret Header**（通用）：读请求头 `X-Webhook-Secret`，比对环境变量 `WEBHOOK_SECRET`

如果两者都没设（`WEBHOOK_SECRET` 为空），**放行**（与原 `APP_PASSWORD` 空时的行为一致）。

### 修改 `web/webhooks.py`

```python
"""
Webhook 路由 — 动态注册，支持 HMAC-SHA256 签名验证和 Shared Secret 认证
"""
import hashlib
import hmac
import os
import threading
from pathlib import Path

import yaml
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

ROOT = Path(__file__).parent.parent
_WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


def _verify_request(request_body: bytes, headers: dict) -> bool:
    """验证 webhook 请求认证。返回 True 表示通过。"""
    if not _WEBHOOK_SECRET:
        return True  # 未配置则放行

    # 方式 1：HMAC-SHA256（GitHub 风格）
    sig_header = headers.get("x-webhook-signature", "")
    if sig_header.startswith("sha256="):
        expected = "sha256=" + hmac.new(
            _WEBHOOK_SECRET.encode(), request_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(sig_header, expected)

    # 方式 2：Shared Secret Header
    secret_header = headers.get("x-webhook-secret", "")
    if secret_header:
        return hmac.compare_digest(secret_header, _WEBHOOK_SECRET)

    return False  # 有 WEBHOOK_SECRET 但请求未携带任何认证


def _load_webhooks():
    config_path = ROOT / "triggers.yaml"
    if not config_path.exists():
        return []
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("webhooks", [])


router = APIRouter()


def _make_handler(config: dict):
    task_type = config["task_type"]
    template = config["description_template"]

    async def handler(request: Request):
        # 认证
        body_bytes = await request.body()
        if not _verify_request(body_bytes, dict(request.headers)):
            raise HTTPException(status_code=401, detail="webhook 认证失败")

        # 解析 JSON
        try:
            import json
            body = json.loads(body_bytes)
        except Exception:
            return JSONResponse({"error": "无效 JSON"}, status_code=400)

        if not isinstance(body, dict):
            return JSONResponse({"error": "body 必须是 JSON object"}, status_code=400)

        # 验证 task_type
        from core.orchestrator import AGENT_MAP
        if task_type not in AGENT_MAP:
            return JSONResponse({"error": f"未知 task_type: {task_type}"}, status_code=400)

        # 生成描述
        try:
            description = template.format(**body)
        except KeyError as e:
            return JSONResponse({"error": f"模板缺少字段: {e}"}, status_code=400)

        # 推入队列，后台执行
        from core import task_queue as tq
        task_id = tq.push(task_type, description)

        def _run():
            try:
                from core.orchestrator import Orchestrator
                Orchestrator().run_task(
                    task_type=task_type,
                    description=description,
                    task_id=task_id,
                    stream_to_db=True,
                )
            except Exception as e:
                tq.fail(task_id, str(e))

        threading.Thread(target=_run, daemon=True).start()
        return JSONResponse({"task_id": task_id})

    return handler


for _cfg in _load_webhooks():
    router.add_api_route(
        _cfg["path"],
        _make_handler(_cfg),
        methods=["POST"],
        name=_cfg.get("name", _cfg["path"]),
    )
```

**注意**：`hmac.new` 应改为 `hmac.new`→正确写法是 `hmac.new(key, msg, digestmod)` 
请确认 Python 标准库用法：`hmac.new(_WEBHOOK_SECRET.encode(), request_body, hashlib.sha256).hexdigest()`

### 修改 `web/app.py`

移除 webhook router 的 `Depends(require_auth)`，因为 webhook 现在有自己的认证：

```python
# 原来：
app.include_router(webhook_router, dependencies=[Depends(require_auth)])

# 改为：
app.include_router(webhook_router)
```

`/api/run` 和 `/api/tasks` 保持原有 `Depends(require_auth)`。

### 新增 `/api/triggers` 端点（加到 `web/app.py`）

```python
@app.get("/api/triggers")
async def get_triggers(_=Depends(require_auth)):
    """返回当前加载的 schedules 和 webhooks 配置（不含敏感信息）"""
    config_path = ROOT / "triggers.yaml"
    if not config_path.exists():
        return JSONResponse({"schedules": [], "webhooks": []})
    with open(config_path, encoding="utf-8") as f:
        import yaml
        data = yaml.safe_load(f) or {}
    return JSONResponse({
        "schedules": data.get("schedules", []),
        "webhooks": [
            {"name": w.get("name"), "path": w.get("path"), "task_type": w.get("task_type")}
            for w in data.get("webhooks", [])
        ],
    })
```

### 更新 `.env.example`

新增：
```
WEBHOOK_SECRET=your-shared-secret-here
```

---

## 任务 2：Next.js 前端完整实现

### 目标

产出一个**可点开、可分享的稳定 URL**，具备：
- 登录页（密码保护，cookie-based session）
- Dashboard（Agent 列表 + 一键触发）
- 实时终端（Supabase Realtime 订阅 task_chunks）
- 任务历史（tasks 列表）
- Triggers 管理（只读展示）

### 技术栈

- **Next.js 14** App Router + TypeScript + Tailwind CSS
- **Supabase JS Client** (`@supabase/supabase-js`) — 前端直接订阅 Realtime
- **Next.js API Routes** — 代理 Render 后端（`APP_PASSWORD` 保留在服务端）
- **Next.js Middleware** — cookie 验证，未登录重定向到 `/login`
- **部署**：Vercel（与现有 Vercel 项目共用，更新 vercel.json）

### 目录结构

```
company-agents/
└── frontend/                 # 原来的 index.html 删掉，整个目录变成 Next.js 项目
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── postcss.config.js
    ├── next.config.ts
    ├── middleware.ts           # 全局 cookie auth 守卫
    ├── .env.local.example     # 前端环境变量示例
    └── src/
        ├── app/
        │   ├── layout.tsx      # Root layout，深色主题
        │   ├── page.tsx        # / → redirect 到 /dashboard
        │   ├── login/
        │   │   └── page.tsx    # 登录页
        │   ├── dashboard/
        │   │   └── page.tsx    # Agent Grid + 触发入口
        │   ├── tasks/
        │   │   ├── page.tsx    # 任务历史列表
        │   │   └── [id]/
        │   │       └── page.tsx # 任务详情 + 实时终端
        │   └── triggers/
        │       └── page.tsx    # Schedules & Webhooks 只读展示
        ├── components/
        │   ├── AgentGrid.tsx   # 8 个 Agent 卡片，每个有触发按钮
        │   ├── Terminal.tsx    # 实时终端，订阅 Supabase Realtime
        │   ├── TaskList.tsx    # 任务列表，带状态标签
        │   └── NavBar.tsx      # 顶部导航
        ├── lib/
        │   ├── supabase.ts     # 前端 Supabase client（anon key）
        │   └── agents.ts       # AGENT_MAP 前端版本（task_type 与显示名称映射）
        └── api/               # Next.js API Routes（代理到 Render）
            ├── run/
            │   └── route.ts   # POST /api/run → 转发到 Render，注入 APP_PASSWORD
            ├── tasks/
            │   └── route.ts   # GET /api/tasks → 转发到 Render
            └── triggers/
                └── route.ts   # GET /api/triggers → 转发到 Render
```

### 关键文件实现要求

#### `frontend/package.json`

```json
{
  "name": "company-agents-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.x",
    "react": "^18",
    "react-dom": "^18",
    "@supabase/supabase-js": "^2",
    "clsx": "^2"
  },
  "devDependencies": {
    "typescript": "^5",
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "tailwindcss": "^3",
    "postcss": "^8",
    "autoprefixer": "^10"
  }
}
```

#### `frontend/middleware.ts`

```typescript
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 放行 /login、/_next、/favicon.ico
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon")
  ) {
    return NextResponse.next();
  }

  // 检查 session cookie
  const session = request.cookies.get("session");
  if (!session?.value) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```

#### `frontend/src/app/login/page.tsx`

- 一个密码输入框 + 提交按钮
- 提交时 POST `/api/auth/login`（Next.js API route）
- API route 验证密码 == `process.env.APP_PASSWORD`，成功则 set cookie `session=authenticated; HttpOnly; Path=/; SameSite=Strict; Max-Age=86400`
- 登录成功跳转 `/dashboard`
- 深色背景，居中卡片，Tailwind 样式

新增 API route `frontend/src/app/api/auth/login/route.ts`：

```typescript
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { password } = await req.json();
  const APP_PASSWORD = process.env.APP_PASSWORD || "";

  if (!APP_PASSWORD || password !== APP_PASSWORD) {
    return NextResponse.json({ error: "密码错误" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set("session", "authenticated", {
    httpOnly: true,
    path: "/",
    sameSite: "strict",
    maxAge: 86400,
  });
  return res;
}
```

#### `frontend/src/app/api/run/route.ts`（代理到 Render）

```typescript
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL!;
const APP_PASSWORD = process.env.APP_PASSWORD || "";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const credentials = Buffer.from(`admin:${APP_PASSWORD}`).toString("base64");

  const resp = await fetch(`${BACKEND_URL}/api/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Basic ${credentials}`,
    },
    body: JSON.stringify(body),
  });

  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
```

同理实现 `/api/tasks/route.ts`（GET）和 `/api/triggers/route.ts`（GET）。

#### `frontend/src/lib/supabase.ts`

```typescript
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

#### `frontend/src/lib/agents.ts`

```typescript
export const AGENTS = [
  { task_type: "code_scan",             name: "代码扫描",   icon: "🔍", desc: "扫描代码变更，识别风险点" },
  { task_type: "doc_refactor",          name: "文档重构",   icon: "📝", desc: "重写文档，使其清晰易读" },
  { task_type: "sales",                 name: "销售助手",   icon: "💼", desc: "生成销售话术和跟进策略" },
  { task_type: "requirements_analysis", name: "需求分析",   icon: "🧩", desc: "拆解需求，输出任务清单" },
  { task_type: "product_page",          name: "产品页面",   icon: "🛒", desc: "生成产品描述和卖点文案" },
  { task_type: "summarize",             name: "内容汇总",   icon: "📊", desc: "汇总产出，生成周报" },
  { task_type: "test",                  name: "测试用例",   icon: "🧪", desc: "生成测试用例和验证脚本" },
  { task_type: "task_tracking",         name: "任务追踪",   icon: "📋", desc: "扫描队列，生成优先级报告" },
] as const;
```

#### `frontend/src/components/Terminal.tsx`

- 接收 `taskId: string` prop
- 用 `supabase.channel(...).on('postgres_changes', ...)` 订阅 `task_chunks` WHERE `task_id=eq.{taskId}`
- 同时调用 `/api/tasks/{taskId}/chunks` 读取历史 chunks（或直接从 Supabase 读）
- 渲染等宽字体黑底绿字终端
- chunk_type 映射：
  - `start` → 灰色："▶ 任务开始"
  - `chunk` → 白色：直接显示 `content.text`
  - `tool` → 黄色：`[工具调用] {content.name}`
  - `done` → 绿色："✓ 完成"
  - `error` → 红色："✗ 错误: {content.message}"
- 自动滚动到底部

```typescript
"use client";
import { useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabase";

interface Chunk {
  id: number;
  chunk_type: string;
  content: Record<string, any>;
  created_at: string;
}

export function Terminal({ taskId }: { taskId: string }) {
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 读取历史
    supabase
      .from("task_chunks")
      .select("*")
      .eq("task_id", taskId)
      .order("id")
      .then(({ data }) => {
        if (data) setChunks(data as Chunk[]);
      });

    // 订阅新增
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
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [taskId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chunks]);

  function renderChunk(chunk: Chunk) {
    const { chunk_type, content } = chunk;
    switch (chunk_type) {
      case "start":
        return <span className="text-gray-500">▶ 任务开始</span>;
      case "chunk":
        return <span className="text-white">{content.text}</span>;
      case "tool":
        return <span className="text-yellow-400">[工具调用] {content.name}</span>;
      case "done":
        return <span className="text-green-400">✓ 完成</span>;
      case "error":
        return <span className="text-red-400">✗ 错误: {content.message}</span>;
      default:
        return <span className="text-gray-400">{JSON.stringify(content)}</span>;
    }
  }

  return (
    <div className="bg-black rounded-lg p-4 font-mono text-sm h-96 overflow-y-auto">
      {chunks.map((chunk) => (
        <div key={chunk.id} className="leading-relaxed">
          {renderChunk(chunk)}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

#### `frontend/src/components/AgentGrid.tsx`

- 展示 8 个 Agent 卡片（从 `lib/agents.ts` 读取）
- 每张卡片：图标 + 名称 + 描述 + 输入框（任务描述） + "运行"按钮
- 点击"运行"时 POST `/api/run`，然后跳转到 `/tasks/{taskId}`
- 运行中显示 loading spinner

#### `frontend/src/app/dashboard/page.tsx`

```typescript
import { AgentGrid } from "@/components/AgentGrid";
import { NavBar } from "@/components/NavBar";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <NavBar />
      <main className="max-w-7xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-2">生产飞轮</h1>
        <p className="text-gray-400 mb-8">选择 Agent，输入任务描述，启动</p>
        <AgentGrid />
      </main>
    </div>
  );
}
```

#### `frontend/src/app/tasks/[id]/page.tsx`

```typescript
import { Terminal } from "@/components/Terminal";
import { NavBar } from "@/components/NavBar";

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <NavBar />
      <main className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="text-xl font-bold mb-4">任务 {params.id}</h1>
        <Terminal taskId={params.id} />
      </main>
    </div>
  );
}
```

#### `frontend/src/app/layout.tsx`

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "生产飞轮",
  description: "一人 + 多 Agent = 千军万马",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" className="dark">
      <body className={`${inter.className} bg-gray-950 text-white antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

在 `frontend/src/app/globals.css` 中包含 Tailwind 基础指令：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

#### `frontend/src/app/tasks/page.tsx`（任务历史）

- 调用 `/api/tasks` 获取任务列表
- 展示表格：任务 ID、类型、描述（截断）、状态、创建时间
- 状态颜色：pending=黄、running=蓝（动态圆点）、done=绿、failed=红
- 每行可点击跳转 `/tasks/{id}`

#### `frontend/src/app/triggers/page.tsx`（Triggers 只读）

- 调用 `/api/triggers` 获取当前配置
- 分两区展示：Schedules（cron + task_type + description）和 Webhooks（path + task_type）
- 只读，不提供编辑

#### `frontend/src/components/NavBar.tsx`

```typescript
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/tasks",     label: "任务历史" },
  { href: "/triggers",  label: "Triggers" },
];

export function NavBar() {
  const pathname = usePathname();
  return (
    <nav className="border-b border-gray-800 bg-gray-900">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center gap-6">
        <span className="font-bold text-white mr-4">飞轮</span>
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "text-sm transition-colors",
              pathname.startsWith(item.href)
                ? "text-white font-medium"
                : "text-gray-400 hover:text-white"
            )}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
```

### 前端环境变量

`frontend/.env.local.example`（部署到 Vercel 时在 Vercel 设置 Environment Variables）：

```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
BACKEND_URL=https://your-app.onrender.com
APP_PASSWORD=your-app-password
```

注意：
- `NEXT_PUBLIC_*` 前缀的变量在浏览器端可见（anon key 和 Supabase URL 是设计上公开的）
- `BACKEND_URL` 和 `APP_PASSWORD` **不加** `NEXT_PUBLIC_` 前缀，仅服务端可见

### `next.config.ts`

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

---

## 任务 3：更新 `vercel.json`

旧的 `vercel.json` 指向静态 `frontend/index.html`，现在改为 Next.js 项目：

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/.next",
  "framework": "nextjs",
  "installCommand": "cd frontend && npm install"
}
```

或者更简单：在 Vercel 项目设置里，把 Root Directory 设为 `frontend`，让 Vercel 自动识别 Next.js。

---

## 验证清单

完成后，按顺序验证：

1. `cd frontend && npm install && npm run build` — 构建无报错
2. `cd frontend && npm run dev` — 本地访问 http://localhost:3000
   - 未登录时访问 `/dashboard` → 跳转 `/login`
   - 输入密码登录 → 跳转 `/dashboard`
   - Dashboard 显示 8 个 Agent 卡片
   - 选一个 Agent，输入描述，点运行 → 跳转 `/tasks/{id}` → Terminal 显示流式输出
   - 访问 `/tasks` → 显示任务历史
   - 访问 `/triggers` → 显示 schedules 和 webhooks
3. 测试 webhook（本地后端先跑）：
   ```bash
   # 无 WEBHOOK_SECRET（放行）
   curl -X POST http://localhost:8000/webhook/code-push \
     -H "Content-Type: application/json" \
     -d '{"ref":"test-branch"}'
   # 应返回 {"task_id": "..."}

   # 有 WEBHOOK_SECRET，用 Shared Secret Header
   curl -X POST http://localhost:8000/webhook/code-push \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: your-secret" \
     -d '{"ref":"test-branch"}'
   # 应返回 {"task_id": "..."}
   ```

---

## 部署步骤

1. **Render 后端**：
   - 在 Render 项目环境变量里加 `WEBHOOK_SECRET`
   - 自动重新部署（或手动触发）

2. **Vercel 前端**：
   - 在 Vercel 项目设置里，`Root Directory` 设为 `frontend`
   - 设置环境变量：`NEXT_PUBLIC_SUPABASE_URL`、`NEXT_PUBLIC_SUPABASE_ANON_KEY`、`BACKEND_URL`、`APP_PASSWORD`
   - 触发部署
   - 部署完成后获得 `https://your-app.vercel.app` — 这就是可分享的稳定 URL

---

## 一句话总结

修复 webhook auth（改 HMAC/Shared-Secret）→ 加 `/api/triggers` 端点 → 用 Next.js 14 重写前端（登录保护 + 实时终端 + 任务历史）→ 部署到 Vercel → 产出可分享稳定 URL。
