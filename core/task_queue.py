"""
任务队列 — Supabase 版
替代原来的 JSON 文件方案
"""

import uuid
from datetime import datetime, timezone
from core.database import get_client


def push(task_type: str, description: str, metadata: dict = None) -> str:
    task_id = str(uuid.uuid4())[:8]
    get_client().table("tasks").insert({
        "id":          task_id,
        "type":        task_type,
        "description": description,
        "status":      "pending",
        "metadata":    metadata or {},
    }).execute()
    return task_id


def pop(task_type: str = None) -> dict | None:
    q = get_client().table("tasks").select("*").eq("status", "pending")
    if task_type:
        q = q.eq("type", task_type)
    res = q.order("created_at").limit(1).execute()
    if not res.data:
        return None
    task = res.data[0]
    get_client().table("tasks").update({"status": "running"}).eq("id", task["id"]).execute()
    return task


def start(task_id: str) -> None:
    get_client().table("tasks").update({"status": "running"}).eq("id", task_id).execute()


def complete(task_id: str, agent: str, output: str) -> None:
    get_client().table("tasks").update({
        "status":       "done",
        "agent":        agent,
        "output":       output[:2000],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", task_id).execute()


def fail(task_id: str, reason: str) -> None:
    get_client().table("tasks").update({
        "status": "failed",
        "output": reason[:2000],
    }).eq("id", task_id).execute()


def list_tasks(status: str = None) -> list[dict]:
    q = get_client().table("tasks").select("*").order("created_at", desc=True).limit(50)
    if status:
        q = q.eq("status", status)
    return q.execute().data or []


def summary() -> str:
    tasks = list_tasks()
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    return f"共 {len(tasks)} 条 | " + " | ".join(f"{k}: {v}" for k, v in counts.items())
