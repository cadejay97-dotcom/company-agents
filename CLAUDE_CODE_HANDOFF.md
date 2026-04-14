# Claude Code Handoff: Trigger Layer Implementation

## 交接目的

这份文件是给 Claude Code 回来复核用的。

本轮 Codex 已完成「触发层 Trigger Layer」的第一版实现，把原本只能被 `/api/run` 手动触发的 Agent 系统，扩展为：

- 定时触发：按 `triggers.yaml` 里的 cron 自动运行 Agent
- 事件触发：按 `triggers.yaml` 里的 webhook 配置动态注册 POST 路由
- 统一流式输出：触发任务同样写入 `task_chunks`，前端可继续通过 Supabase Realtime 看终端输出

## 已完成文件

新增：

- `core/scheduler.py`
- `web/webhooks.py`
- `triggers.yaml`
- `CLAUDE_CODE_HANDOFF.md`

修改：

- `web/app.py`
- `core/orchestrator.py`
- `core/task_queue.py`
- `requirements.txt`

## 核心实现

### 1. `core/scheduler.py`

职责：

- 读取项目根目录 `triggers.yaml`
- 解析 `schedules`
- 用 `APScheduler BackgroundScheduler` 注册 cron job
- job 触发时调用 `Orchestrator().run_task(..., stream_to_db=True)`
- 提供 `start_scheduler()` / `stop_scheduler()`

设计点：

- 默认时区是 `Asia/Shanghai`
- 可用环境变量 `TRIGGER_TIMEZONE` 覆盖
- 每个 job 设置：
  - `replace_existing=True`
  - `max_instances=1`
  - `coalesce=True`

注意：

- 默认配置里没有使用数字 weekday，例如 `1-5`
- 改成了 `mon-fri` / `fri`
- 原因是 APScheduler 的星期数字语义和普通 cron 容易让人误判，命名 weekday 更安全

### 2. `web/webhooks.py`

职责：

- 读取 `triggers.yaml` 中的 `webhooks`
- 动态注册每条 webhook 的 POST 路由
- body 必须是 JSON object
- 用 `description_template.format(**body)` 生成任务描述
- 先 `task_queue.push(...)` 创建任务，立即返回 `{"task_id": "..."}`
- 后台线程执行 Agent
- Agent 输出通过 `stream_to_db=True` 写入 Supabase `task_chunks`

错误处理：

- JSON 无效：返回 400
- body 不是 object：返回 400
- `task_type` 未知：返回 400
- template 缺字段：返回 400，例如缺 `{ref}` 时提示字段名

### 3. `web/app.py`

接入点：

- 引入 `asynccontextmanager`
- FastAPI 使用 `lifespan`
- 应用启动时 `start_scheduler()`
- 应用关闭时 `stop_scheduler()`
- `include_router(webhook_router, dependencies=[Depends(require_auth)])`

安全点：

- webhook router 复用了现有 Basic Auth
- 如果 `APP_PASSWORD` 设置了，webhook 也需要认证
- 如果 `APP_PASSWORD` 为空，保持原项目行为：放行

`/api/run` 也已改成复用 `Orchestrator.run_task(..., task_id=..., stream_to_db=True)`，避免手写重复的 Agent 执行逻辑。

### 4. `core/orchestrator.py`

主要变化：

- `dispatch(task, on_chunk=None)` 支持传入 chunk 回调
- dispatch 开始时调用 `task_queue.start(task["id"])`
- `run_task()` 新增参数：
  - `task_id: str = None`
  - `on_chunk=None`
  - `stream_to_db: bool = False`

行为：

- 没有传 `task_id` 时，保持原行为：新建任务并执行
- 传了 `task_id` 时，复用已有任务记录执行
- `stream_to_db=True` 时，把 Agent chunk 写入 `task_chunks`
- 出错时：
  - 更新任务为 failed
  - 写入 error chunk
  - 再抛出异常给调用方

### 5. `core/task_queue.py`

新增：

- `start(task_id: str)`

用途：

- 把任务状态从 `pending` 更新为 `running`
- 让 `/api/run`、webhook、scheduler 这种“先 push，后后台执行”的路径有统一状态流转

### 6. `requirements.txt`

新增：

```txt
apscheduler>=3.10.0
pyyaml>=6.0
```

## 当前 `triggers.yaml`

```yaml
schedules:
  - name: 每日任务追踪
    cron: "0 9 * * mon-fri"
    task_type: task_tracking
    description: "扫描队列，生成今日优先级报告"

  - name: 每周汇总
    cron: "0 18 * * fri"
    task_type: summarize
    description: "汇总本周所有 Agent 产出，生成周报"

webhooks:
  - name: 新代码提交
    path: /webhook/code-push
    task_type: code_scan
    description_template: "扫描最新提交的代码变更: {ref}"

  - name: 新需求文档
    path: /webhook/new-requirement
    task_type: requirements_analysis
    description_template: "拆解新需求: {title}"
```

## 已验证

本地已执行：

```bash
python -m compileall core web
```

结果：通过。

```bash
python -c "from web.app import app; print(app.title); print(sorted([r.path for r in app.routes if r.path.startswith('/webhook')]))"
```

结果：

```txt
公司智能体飞轮 API
['/webhook/code-push', '/webhook/new-requirement']
```

```bash
python -c "from core.scheduler import start_scheduler, stop_scheduler; start_scheduler(); import core.scheduler as s; print(len(s._scheduler.get_jobs())); stop_scheduler()"
```

结果：

```txt
[Scheduler] 已注册: 每日任务追踪 (0 9 * * mon-fri)
[Scheduler] 已注册: 每周汇总 (0 18 * * fri)
2
```

```bash
python -c "from fastapi.testclient import TestClient; from web.app import app; client = TestClient(app); print(client.get('/health').json())"
```

结果：

```txt
{'status': 'ok'}
```

## 未做真实端到端触发

没有真实触发 Agent 任务。

原因：

- 真实执行会访问 Supabase
- 真实执行会访问 Anthropic
- 可能消耗 token / 产生真实数据库记录

建议 Claude Code 下一步在确认环境变量齐全后执行：

```bash
curl -X POST "$BACKEND_URL/webhook/code-push" \
  -u "admin:$APP_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"ref":"manual-test"}'
```

然后检查：

- `tasks` 是否出现新任务
- `tasks.status` 是否从 `pending` 到 `running` 再到 `done` 或 `failed`
- `task_chunks` 是否出现 `start` / `chunk` / `tool` / `done` 或 `error`
- 前端 Realtime 是否能看到输出

## 需要 Claude Code 重点复核

1. 是否接受 webhook 使用同一套 Basic Auth。

当前实现更安全，但如果外部平台不能设置 Basic Auth，需要改成：

- shared secret header
- query token
- HMAC signature
- 或对指定 webhook 关闭认证

2. scheduler 是否应该在多实例部署时只跑一个实例。

Render 如果横向扩容，多实例会重复跑 schedule。
当前 Render 免费/单实例通常没问题。
如果未来扩容，需要加分布式锁或让 scheduler 独立成 worker。

3. `Orchestrator.run_task()` 现在会在 `dispatch()` 开头把任务标成 running。

这让 `/api/run`、webhook、scheduler 的状态一致。
但 `run_pending()` 中 `pop()` 已经标记 running，之后 `dispatch()` 会再更新一次 running。
这是无害重复写入；如果想更干净，可以后续拆成 `mark_running=True` 参数。

4. error chunk 可能重复写失败状态。

`Orchestrator.run_task()` 已经会 `task_queue.fail()`。
`web/app.py` 和 `web/webhooks.py` 外层线程也有兜底 `fail()`。
这也是无害重复写入；保留原因是防止异常发生在 Orchestrator 外层。

## 下一步建议

优先级从高到低：

1. 在真实 Supabase + Anthropic 环境跑一次 webhook 端到端。
2. 在 Render 部署后观察 scheduler 启动日志，确认只注册 2 个 job。
3. 给 webhook 增加更适合生产的签名认证。
4. 给 `/api/triggers` 做一个只读调试端点，返回当前加载到的 schedules/webhooks。
5. 给 scheduler 增加任务执行审计 metadata，例如 `fired_at`。

## 给 Claude Code 的一句话总结

Trigger Layer 已完成可导入、可注册、可后台执行的第一版；当前实现重点保持了原系统的 Supabase Realtime 终端体验，同时把 webhook 纳入现有密码保护。下一步主要不是继续写代码，而是在真实云环境里做一次 webhook 和 scheduler 的端到端验证。
