"""Webhook 触发入口，支持 HMAC 签名或 Shared Secret 认证。"""

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core import task_queue as tq
from core.orchestrator import AGENT_MAP, Orchestrator

ROOT = Path(__file__).resolve().parent.parent
TRIGGERS_FILE = ROOT / "triggers.yaml"
_WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

router = APIRouter()


def _verify_request(request_body: bytes, headers: dict) -> bool:
    """验证 webhook 请求认证。WEBHOOK_SECRET 未配置时放行。"""
    if not _WEBHOOK_SECRET:
        return True

    signature = headers.get("x-webhook-signature", "")
    if signature.startswith("sha256="):
        expected = "sha256=" + hmac.new(
            _WEBHOOK_SECRET.encode(),
            request_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    secret = headers.get("x-webhook-secret", "")
    if secret:
        return hmac.compare_digest(secret, _WEBHOOK_SECRET)

    return False


def _load_webhooks() -> list[dict]:
    if not TRIGGERS_FILE.exists():
        return []
    data = yaml.safe_load(TRIGGERS_FILE.read_text(encoding="utf-8")) or {}
    return data.get("webhooks") or []


def _make_handler(config: dict):
    async def handler(request: Request):
        body_bytes = await request.body()
        if not _verify_request(body_bytes, dict(request.headers)):
            raise HTTPException(status_code=401, detail="webhook 认证失败")

        try:
            body = json.loads(body_bytes)
        except Exception:
            return JSONResponse({"error": "请求 body 必须是 JSON"}, status_code=400)

        if not isinstance(body, dict):
            return JSONResponse({"error": "请求 body 必须是 JSON object"}, status_code=400)

        name = config.get("name", "未命名 webhook")
        task_type = config.get("task_type")
        template = config.get("description_template", "")

        if task_type not in AGENT_MAP:
            return JSONResponse({"error": f"未知 task_type: {task_type}"}, status_code=400)

        try:
            description = template.format(**body)
        except KeyError as exc:
            return JSONResponse(
                {"error": f"description_template 缺少字段: {exc.args[0]}"},
                status_code=400,
            )

        metadata = {
            "trigger": "webhook",
            "trigger_name": name,
            "path": config.get("path"),
            "payload": body,
        }
        task_id = tq.push(task_type, description, metadata)

        def _run():
            try:
                Orchestrator().run_task(
                    task_type=task_type,
                    description=description,
                    metadata=metadata,
                    task_id=task_id,
                    stream_to_db=True,
                )
            except Exception as exc:
                tq.fail(task_id, str(exc))

        threading.Thread(target=_run, daemon=True).start()
        return JSONResponse({"task_id": task_id})

    return handler


for webhook in _load_webhooks():
    path = webhook.get("path", "")
    name = webhook.get("name", path or "webhook")
    if not path.startswith("/"):
        print(f"[Webhook] 跳过 {name}: path 必须以 / 开头")
        continue
    router.add_api_route(path, _make_handler(webhook), methods=["POST"], name=name)
