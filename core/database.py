"""
Supabase 客户端 — 懒加载单例
后端使用 SUPABASE_SERVICE_ROLE_KEY（完全权限，绝不暴露给前端）
"""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError(
                "请设置环境变量: SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY"
            )
        _client = create_client(url, key)
    return _client


def insert_chunk(task_id: str, chunk_type: str, content: dict) -> None:
    """将一个 Agent 输出 chunk 写入 Supabase（供前端 Realtime 订阅）"""
    get_client().table("task_chunks").insert({
        "task_id":    task_id,
        "chunk_type": chunk_type,
        "content":    content,
    }).execute()
