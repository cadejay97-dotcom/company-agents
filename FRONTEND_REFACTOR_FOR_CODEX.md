# 前端重构任务（给 Codex）

## 背景：后端架构已经完成了一次重大重构

这份文档要求你重构 `frontend/` 目录，让前端反映后端已经完成的架构变化。

后端刚刚完成的变化：

**旧架构（已废弃）**：8 个按岗位命名的 Agent 平铺在一起（代码扫描、文档重构、销售助手……）

**新架构（已生效）**：9 个 Agent 按六层母结构组织：

| 层 | task_type | 职责 |
|----|-----------|------|
| 感知层 Perception | `requirements_analysis`, `summarize` | 感知需求与内部状态 |
| 判断层 Judgment | `judgment` | 系统中枢，决定优先级和"够好"标准 |
| 生成层 Generation | `doc_refactor`, `product_page` | 把判断转化为具体产出 |
| 验证层 Validation | `code_scan`, `test` | PASS/FAIL 把关，失败时阻断下游 |
| 交换层 Exchange | `sales` | 把内部产出转化为外部价值交换 |
| 治理层 Governance | `task_tracking` | 维持系统状态和秩序 |

后端新增了三个治理文件（存在 `workspace/` 目录）：
- `STATE.json`：单一事实源，记录当前目标、阶段、约束、阻塞项
- `DECISIONS.md`：追加式决策记录
- `HANDOFF_PROTOCOL.md`：Agent 交接协议

验证层 Agent（`code_scan`、`test`）执行完后会在输出末尾写 `VERDICT: PASS` 或 `VERDICT: FAIL`，后端已实现 gate 逻辑，FAIL 时阻断下游。

---

## 当前前端的问题

`frontend/src/lib/agents.ts` 里 8 个 Agent 是平铺的，没有层的概念。
`frontend/src/app/dashboard/page.tsx` 显示一个无差别的 4 列 Agent 卡片网格。
没有任何地方展示 STATE.json、DECISIONS.md 或 VERDICT 信息。

---

## 你需要做的事

### 任务 1：更新 `agents.ts`

把 `AGENTS` 数组改为按层组织，添加 `layer` 字段和 `isGate` 标记。新增 `judgment` Agent。

```typescript
// frontend/src/lib/agents.ts

export type Layer = 
  | "perception"
  | "judgment"  
  | "generation"
  | "validation"
  | "exchange"
  | "governance";

export const LAYERS: { id: Layer; label: string; desc: string }[] = [
  { id: "perception",  label: "感知层",  desc: "感知需求与内部状态" },
  { id: "judgment",    label: "判断层",  desc: "系统中枢 · 定义标准与优先级" },
  { id: "generation",  label: "生成层",  desc: "把判断转化为具体产出" },
  { id: "validation",  label: "验证层",  desc: "PASS / FAIL 把关，失败阻断下游" },
  { id: "exchange",    label: "交换层",  desc: "把产出转化为外部价值交换" },
  { id: "governance",  label: "治理层",  desc: "维持系统状态与秩序" },
];

export const AGENTS = [
  // 感知层
  {
    task_type: "requirements_analysis",
    icon: "RA",
    name: "需求分析",
    desc: "拆解需求，输出任务清单",
    prompt: "拆解这条需求，输出用户故事、验收标准和优先级。",
    layer: "perception" as Layer,
    isGate: false,
  },
  {
    task_type: "summarize",
    icon: "SU",
    name: "内容汇总",
    desc: "汇总产出，生成状态摘要",
    prompt: "汇总近期 Agent 产出，生成执行摘要、关键发现和待跟进事项。",
    layer: "perception" as Layer,
    isGate: false,
  },
  // 判断层
  {
    task_type: "judgment",
    icon: "JD",
    name: "判断中枢",
    desc: "决定优先级，定义'够好'标准，写入决策记录",
    prompt: "读取当前系统状态和感知层输出，判断最优先的问题，选定方向，定义验收标准，推送任务。",
    layer: "judgment" as Layer,
    isGate: false,
  },
  // 生成层
  {
    task_type: "doc_refactor",
    icon: "DR",
    name: "文档重构",
    desc: "重写文档，使其清晰可执行",
    prompt: "重构指定文档，保留事实，提升结构和可执行性。",
    layer: "generation" as Layer,
    isGate: false,
  },
  {
    task_type: "product_page",
    icon: "PP",
    name: "产品页面",
    desc: "生成产品描述和卖点文案",
    prompt: "基于产品信息生成页面文案，包含标题、卖点和行动按钮。",
    layer: "generation" as Layer,
    isGate: false,
  },
  // 验证层
  {
    task_type: "code_scan",
    icon: "CS",
    name: "代码扫描",
    desc: "扫描代码，输出 PASS / FAIL 判决",
    prompt: "扫描当前代码库，找出最高优先级的问题，输出最终判决。",
    layer: "validation" as Layer,
    isGate: true,
  },
  {
    task_type: "test",
    icon: "QA",
    name: "测试验证",
    desc: "设计测试用例，输出 PASS / FAIL 判决",
    prompt: "根据当前需求和实现，设计测试用例，执行验证，输出最终判决。",
    layer: "validation" as Layer,
    isGate: true,
  },
  // 交换层
  {
    task_type: "sales",
    icon: "SA",
    name: "销售助手",
    desc: "生成销售话术和跟进策略",
    prompt: "整理销售材料，输出客户可理解的方案、价值和下一步。",
    layer: "exchange" as Layer,
    isGate: false,
  },
  // 治理层
  {
    task_type: "task_tracking",
    icon: "TT",
    name: "任务追踪",
    desc: "扫描队列，更新系统状态",
    prompt: "扫描当前任务队列，更新 STATE.json，生成今日优先级报告。",
    layer: "governance" as Layer,
    isGate: false,
  },
] as const;

export type AgentTaskType = (typeof AGENTS)[number]["task_type"];
export const AGENT_BY_TYPE = Object.fromEntries(
  AGENTS.map((a) => [a.task_type, a])
) as Record<AgentTaskType, (typeof AGENTS)[number]>;

export const AGENTS_BY_LAYER = LAYERS.map((layer) => ({
  ...layer,
  agents: AGENTS.filter((a) => a.layer === layer.id),
}));
```

---

### 任务 2：重构 `AgentGrid.tsx`

从平铺卡片改为按层分组显示。要求：

- 每层有一个 section header，显示层名 + 层描述
- 判断层视觉上最突出（border 颜色更亮，或加标签 `系统中枢`）
- 验证层卡片加 `GATE` 标签，表示这个 Agent 的输出会阻断下游
- 感知层和治理层用更低调的视觉（Agent 较"基础"）
- 其余逻辑（textarea、运行按钮、loading 状态、路由到 /tasks/:id）保持不变

参考当前实现在 `frontend/src/components/AgentGrid.tsx`。

层的颜色建议（基于现有深色主题 `bg-ink` / `text-leaf`）：
- 感知层：默认灰色
- 判断层：`text-leaf`（绿色）+ border 加亮
- 生成层：默认灰色
- 验证层：`text-amber-400`（琥珀色）+ `GATE` badge
- 交换层：默认灰色
- 治理层：`text-stone-500`（更暗）

---

### 任务 3：新增 `StatePanel` 组件

在 Dashboard 顶部（Agent 网格上方）加一个状态面板，展示 STATE.json 的关键字段。

**需要新增的后端 API 路由** `frontend/src/app/api/state/route.ts`：
```typescript
// 代理到 Render 后端的 /state 端点
import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) return NextResponse.json({ error: "no backend" }, { status: 500 });
  
  try {
    const res = await fetch(`${backendUrl}/state`, {
      headers: {
        Authorization: `Basic ${Buffer.from(`admin:${process.env.APP_PASSWORD}`).toString("base64")}`,
      },
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "backend unreachable" }, { status: 502 });
  }
}
```

**需要新增的后端 Python 端点** `web/app.py`，在现有路由里加：
```python
@app.get("/state")
async def get_state(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    import json
    from pathlib import Path
    state_file = Path(__file__).parent.parent / "workspace" / "STATE.json"
    if not state_file.exists():
        return {"error": "STATE.json not found"}
    return json.loads(state_file.read_text(encoding="utf-8"))
```

**`StatePanel` 组件**（`frontend/src/components/StatePanel.tsx`）：
- 展示字段：`current_goal`、`phase`、`constraints`（列表）、`blockers`（列表，有内容时用红色）
- 样式：一个横向的信息条，深色背景，紧凑排列
- 如果后端不可达，静默失败（不显示面板）

---

### 任务 4：验证层任务详情显示 VERDICT

在 `Terminal` 组件中，如果 `done` 类型的 chunk 里有 `verdict` 字段：
- `verdict: "pass"` → 在终端顶部或底部显示绿色 `✓ VERDICT: PASS` badge
- `verdict: "fail"` → 显示红色 `✗ VERDICT: FAIL` badge + 文字"下游任务已阻断"

chunk 的数据结构（`done` 类型）：
```json
{ "type": "done", "verdict": "pass" }
```
或
```json
{ "type": "done", "verdict": "fail" }
```

在 `renderChunk` 里更新 `done` case：
```typescript
case "done":
  const verdict = content.verdict as string | undefined;
  if (verdict === "pass") return <span className="text-emerald-400 font-semibold">✓ VERDICT: PASS · 完成</span>;
  if (verdict === "fail") return <span className="text-red-400 font-semibold">✗ VERDICT: FAIL · 下游任务已阻断</span>;
  return <span className="text-emerald-300">完成</span>;
```

---

### 任务 5：NavBar 加"系统状态"入口（可选，低优先级）

在 NavBar 的导航里加一个 `系统状态` 链接，指向新页面 `/state`，显示完整的 STATE.json 和 DECISIONS.md 内容。

---

## 不要改的东西

- `login/page.tsx` — 登录页不动
- `tasks/page.tsx` — 任务历史不动
- `middleware.ts` — 认证逻辑不动
- `lib/supabase.ts`、`lib/session.ts`、`lib/types.ts` — 不动
- Tailwind 主题变量（`bg-ink`、`text-leaf`、`border-line`、`bg-panel`）— 保持现有深色主题

---

## 执行顺序

1. 更新 `agents.ts`（加 layer 字段，加 judgment Agent）
2. 重构 `AgentGrid.tsx`（按层分组）
3. 新增后端 `/state` 端点（`web/app.py`）
4. 新增前端 `/api/state` 代理路由
5. 新增 `StatePanel` 组件，嵌入 dashboard
6. 更新 `Terminal` 组件显示 VERDICT badge
7. 本地 `npm run dev` 验证，确认：
   - Dashboard 按六层分组显示
   - 判断层视觉突出
   - 验证层有 GATE 标签
   - StatePanel 能展示（或静默失败）
   - VERDICT badge 在 done chunk 里正确显示

---

## 文件路径速查

```
frontend/
  src/
    lib/
      agents.ts           ← 任务1：完全重写
    components/
      AgentGrid.tsx       ← 任务2：重构
      StatePanel.tsx      ← 任务3：新建
      Terminal.tsx        ← 任务4：更新 done case
      NavBar.tsx          ← 任务5（可选）
    app/
      dashboard/
        page.tsx          ← 嵌入 StatePanel
      api/
        state/
          route.ts        ← 任务3：新建

web/
  app.py                  ← 任务3：加 /state 端点
```

---

## 关键约束

- 前端 `BACKEND_URL` 环境变量已指向 `https://company-agents.onrender.com`
- 后端 HTTPBasic 认证密码：`flywheel2026`（`APP_PASSWORD` 环境变量）
- 前端认证逻辑不变：HttpOnly cookie session，middleware 守卫
- 深色主题不变，审美基调：克制、信息密度高、无多余装饰
