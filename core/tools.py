"""
公共工具集 — 所有 Agent 可调用的工具定义 + 实现
"""

import json
from datetime import datetime
from pathlib import Path
from core import task_queue

WORKSPACE = Path(__file__).parent.parent / "workspace"
_STATE_FILE = WORKSPACE / "STATE.json"
_DECISIONS_FILE = WORKSPACE / "DECISIONS.md"


# ─── 工具实现 ────────────────────────────────────────────────────────────────

def read_file(path: str) -> str:
    """读取 workspace 内的文件"""
    target = WORKSPACE / path
    if not target.exists():
        return f"[错误] 文件不存在: {path}"
    return target.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """写入文件到 workspace"""
    target = WORKSPACE / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"已写入: {path} ({len(content)} 字符)"


def list_directory(path: str = "") -> str:
    """列出 workspace 目录内容"""
    target = WORKSPACE / path
    if not target.exists():
        return f"[错误] 目录不存在: {path}"
    entries = []
    for item in sorted(target.iterdir()):
        kind = "📁" if item.is_dir() else "📄"
        entries.append(f"{kind} {item.name}")
    return "\n".join(entries) if entries else "(空目录)"


def read_tasks(status: str = "pending") -> str:
    """查看任务队列"""
    tasks = task_queue.list_tasks(status)
    if not tasks:
        return f"没有 {status} 状态的任务"
    lines = []
    for t in tasks:
        lines.append(f"[{t['id']}] {t['type']} | {t['description'][:60]}")
    return "\n".join(lines)


def add_task(task_type: str, description: str) -> str:
    """向任务队列添加新任务"""
    task_id = task_queue.push(task_type, description)
    return f"任务已创建: {task_id} ({task_type})"


def complete_task(task_id: str, output_summary: str) -> str:
    """标记任务为已完成（由 Orchestrator 调用，Agent 不直接调用）"""
    task_queue.complete(task_id, agent="agent", output=output_summary)
    return f"任务 {task_id} 已完成"


def update_state(updates: str) -> str:
    """更新 STATE.json 中的字段。updates 为 JSON 字符串，仅更新指定字段，不覆盖其他字段。"""
    try:
        changes = json.loads(updates)
    except json.JSONDecodeError as e:
        return f"[错误] updates 必须是合法 JSON: {e}"

    state = {}
    if _STATE_FILE.exists():
        try:
            state = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    protected = {"_meta"}
    applied = []
    for key, value in changes.items():
        if key in protected:
            continue
        state[key] = value
        applied.append(key)

    state.setdefault("_meta", {})["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"STATE.json 已更新字段: {', '.join(applied)}"


def log_decision(title: str, decision: str, reason: str, scope: str = "") -> str:
    """向 DECISIONS.md 追加一条决策记录。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = (
        f"\n## {timestamp} — {title}\n\n"
        f"**决策**: {decision}  \n"
        f"**原因**: {reason}  \n"
        + (f"**影响范围**: {scope}  \n" if scope else "")
        + "\n---\n"
    )
    existing = _DECISIONS_FILE.read_text(encoding="utf-8") if _DECISIONS_FILE.exists() else ""
    _DECISIONS_FILE.write_text(existing + entry, encoding="utf-8")
    return f"决策已记录: {title}"


# ─── API 工具定义 ──────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "读取 workspace 目录下的文件内容。path 为相对路径，如 'shared/context.json'",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对于 workspace/ 的文件路径"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "将内容写入 workspace 目录下的文件。自动创建父目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对路径，如 'outputs/doc_refactor/result.md'"},
                "content": {"type": "string", "description": "文件内容"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "列出 workspace 内某目录的文件和子目录",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对路径，默认为根目录"}
            },
            "required": [],
        },
    },
    {
        "name": "read_tasks",
        "description": "查看任务队列。status 可为 pending / running / done / failed",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "done", "failed"],
                    "description": "过滤状态",
                }
            },
            "required": [],
        },
    },
    {
        "name": "add_task",
        "description": "向任务队列添加一个新任务，供其他 Agent 领取",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "任务类型，如 code_scan / doc_refactor / requirements_analysis 等",
                },
                "description": {"type": "string", "description": "任务的具体描述"},
            },
            "required": ["task_type", "description"],
        },
    },
    {
        "name": "update_state",
        "description": (
            "更新 workspace/STATE.json 中的系统状态字段。"
            "用于记录当前目标、活跃任务、阻塞项、最新决策等。"
            "updates 必须是合法 JSON 字符串，如 '{\"active_tasks\": [\"task_a\"], \"last_decision\": \"选择方向 X\"}'。"
            "不会覆盖 _meta 字段。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "string",
                    "description": "JSON 字符串，包含要更新的字段和新值",
                }
            },
            "required": ["updates"],
        },
    },
    {
        "name": "log_decision",
        "description": "向 workspace/DECISIONS.md 追加一条决策记录。用于记录重要的方向选择、优先级判断、标准定义。",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "决策标题，简洁描述这是什么决策"},
                "decision": {"type": "string", "description": "决策内容"},
                "reason": {"type": "string", "description": "做出此决策的原因"},
                "scope": {"type": "string", "description": "影响范围（可选）"},
            },
            "required": ["title", "decision", "reason"],
        },
    },
]

# 工具名 → 函数 的映射
TOOL_REGISTRY: dict = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "read_tasks": read_tasks,
    "add_task": add_task,
    "update_state": update_state,
    "log_decision": log_decision,
}
