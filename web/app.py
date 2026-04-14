"""
FastAPI 后端 — 部署在 Render
前端在 Vercel，通过 CORS 跨域调用
实时输出通过 Supabase Realtime 推送（不再需要 SSE）
"""

import os
import sys
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from core import task_queue as tq
from core.scheduler import start_scheduler, stop_scheduler
from core.orchestrator import AGENT_MAP
from web.webhooks import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="公司智能体飞轮 API", lifespan=lifespan)
security = HTTPBasic(auto_error=False)

# ── CORS（允许 Vercel 前端跨域访问） ─────────────────────────────────────────
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 访问密码 ──────────────────────────────────────────────────────────────────
_APP_PASSWORD = os.environ.get("APP_PASSWORD", "")


def require_auth(credentials: HTTPBasicCredentials | None = Depends(security)):
    if not _APP_PASSWORD:
        return
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="认证失败",
            headers={"WWW-Authenticate": "Basic"},
        )
    ok = (
        secrets.compare_digest(credentials.username.encode(), b"admin")
        and secrets.compare_digest(credentials.password.encode(), _APP_PASSWORD.encode())
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="认证失败",
            headers={"WWW-Authenticate": "Basic"},
        )


# ── 路由 ──────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/state")
async def get_state(_=Depends(require_auth)):
    state_file = ROOT / "workspace" / "STATE.json"
    if not state_file.exists():
        return JSONResponse({"error": "STATE.json not found"}, status_code=404)
    try:
        import json
        return JSONResponse(json.loads(state_file.read_text(encoding="utf-8")))
    except Exception as exc:
        return JSONResponse({"error": f"STATE.json unreadable: {exc}"}, status_code=500)


@app.post("/api/run")
async def run_task(request: Request, _=Depends(require_auth)):
    body = await request.json()
    task_type   = body.get("task_type", "").strip()
    description = body.get("description", "").strip()

    if not task_type or not description:
        return JSONResponse({"error": "task_type 和 description 不能为空"}, status_code=400)
    if task_type not in AGENT_MAP:
        return JSONResponse({"error": f"未知 task_type: {task_type}"}, status_code=400)

    task_id = tq.push(task_type, description)

    def _run():
        try:
            from core.orchestrator import Orchestrator
            orch = Orchestrator()
            orch.run_task(
                task_type=task_type,
                description=description,
                task_id=task_id,
                stream_to_db=True,
            )
        except Exception as e:
            tq.fail(task_id, str(e))

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"task_id": task_id})


@app.get("/api/tasks")
async def get_tasks(_=Depends(require_auth)):
    return JSONResponse({"tasks": tq.list_tasks()})


@app.get("/api/triggers")
async def get_triggers(_=Depends(require_auth)):
    config_path = ROOT / "triggers.yaml"
    if not config_path.exists():
        return JSONResponse({"schedules": [], "webhooks": []})

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    webhooks = [
        {
            "name": item.get("name"),
            "path": item.get("path"),
            "task_type": item.get("task_type"),
        }
        for item in data.get("webhooks", [])
    ]
    return JSONResponse({
        "schedules": data.get("schedules", []),
        "webhooks": webhooks,
    })


app.include_router(webhook_router)
