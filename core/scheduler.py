"""
定时触发器
启动时读取 triggers.yaml，将 schedules 注册成 APScheduler cron job。
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from core.orchestrator import AGENT_MAP, Orchestrator

ROOT = Path(__file__).resolve().parent.parent
TRIGGERS_FILE = ROOT / "triggers.yaml"

_scheduler: BackgroundScheduler | None = None


def _load_triggers() -> dict:
    if not TRIGGERS_FILE.exists():
        return {"schedules": [], "webhooks": []}
    data = yaml.safe_load(TRIGGERS_FILE.read_text(encoding="utf-8")) or {}
    return {
        "schedules": data.get("schedules") or [],
        "webhooks": data.get("webhooks") or [],
    }


def _build_cron_trigger(cron_expr: str, timezone: ZoneInfo) -> CronTrigger:
    fields = cron_expr.split()
    if len(fields) != 5:
        raise ValueError(f"cron 必须是 5 段表达式: {cron_expr}")
    minute, hour, day, month, day_of_week = fields
    return CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        timezone=timezone,
    )


def _run_scheduled_task(schedule: dict) -> None:
    name = schedule.get("name", "未命名定时任务")
    task_type = schedule["task_type"]
    description = schedule["description"]
    metadata = {
        "trigger": "schedule",
        "trigger_name": name,
        "cron": schedule.get("cron"),
    }
    print(f"[Scheduler] 触发: {name} -> {task_type}")
    Orchestrator().run_task(
        task_type=task_type,
        description=description,
        metadata=metadata,
        stream_to_db=True,
    )


def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    timezone_name = os.environ.get("TRIGGER_TIMEZONE", "Asia/Shanghai")
    timezone = ZoneInfo(timezone_name)
    scheduler = BackgroundScheduler(timezone=timezone)
    config = _load_triggers()

    for item in config["schedules"]:
        name = item.get("name", "未命名定时任务")
        task_type = item.get("task_type")
        cron_expr = item.get("cron")
        description = item.get("description")

        if not task_type or task_type not in AGENT_MAP:
            print(f"[Scheduler] 跳过 {name}: 未知 task_type={task_type}")
            continue
        if not cron_expr or not description:
            print(f"[Scheduler] 跳过 {name}: cron 和 description 不能为空")
            continue

        scheduler.add_job(
            _run_scheduled_task,
            trigger=_build_cron_trigger(cron_expr, timezone),
            args=[item],
            id=f"schedule:{name}",
            name=name,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        print(f"[Scheduler] 已注册: {name} ({cron_expr})")

    scheduler.start()
    _scheduler = scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
