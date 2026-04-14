"""
Orchestrator — 任务路由中枢
将任务分发给对应的 Agent，收集结果
"""

from layers import (
    CodeScannerAgent,
    DocRefactorAgent,
    JudgmentAgent,
    SalesAgent,
    RequirementsAnalystAgent,
    ProductPageAgent,
    SummarizerAgent,
    TesterAgent,
    TaskTrackerAgent,
)
from core import task_queue
from core.database import insert_chunk


# 任务类型 → Agent 类 的映射
AGENT_MAP = {
    # 感知层
    "requirements_analysis":  RequirementsAnalystAgent,
    "summarize":              SummarizerAgent,
    # 判断层
    "judgment":               JudgmentAgent,
    # 生成层
    "doc_refactor":           DocRefactorAgent,
    "product_page":           ProductPageAgent,
    # 验证层
    "code_scan":              CodeScannerAgent,
    "test":                   TesterAgent,
    # 交换层
    "sales":                  SalesAgent,
    # 治理层
    "task_tracking":          TaskTrackerAgent,
}

# 验证层 Agent：返回 FAIL 时阻断下游
VALIDATION_TASK_TYPES = {"code_scan", "test"}


class GateFailedError(Exception):
    """验证层判决 FAIL，下游任务已中止。"""
    def __init__(self, task_type: str, task_id: str, reason: str):
        self.task_type = task_type
        self.task_id = task_id
        super().__init__(f"[Gate] {task_type}/{task_id} 返回 FAIL — {reason}")


class Orchestrator:
    def __init__(self):
        # 懒加载 Agent 实例（避免重复初始化 client）
        self._agents: dict = {}

    def _get_agent(self, task_type: str):
        if task_type not in self._agents:
            agent_cls = AGENT_MAP.get(task_type)
            if agent_cls is None:
                raise ValueError(f"未知任务类型: {task_type}。可用类型: {list(AGENT_MAP.keys())}")
            self._agents[task_type] = agent_cls()
        return self._agents[task_type]

    def dispatch(self, task: dict, on_chunk=None) -> dict:
        """分发单个任务给对应 Agent，验证层任务自动检查 gate。"""
        task_queue.start(task["id"])
        agent = self._get_agent(task["type"])
        result = agent.run(task, on_chunk=on_chunk)

        # Gate 检查：验证层返回 FAIL 时中止
        if task["type"] in VALIDATION_TASK_TYPES:
            verdict = result.get("verdict")
            if verdict == "fail":
                reason = f"验证层判决 FAIL（{task['type']}）"
                task_queue.fail(task["id"], reason)
                raise GateFailedError(task["type"], task["id"], reason)

        task_queue.complete(task["id"], agent=agent.name, output=result["output"][:500])
        return result

    def run_task(
        self,
        task_type: str,
        description: str,
        metadata: dict = None,
        *,
        task_id: str = None,
        on_chunk=None,
        stream_to_db: bool = False,
    ) -> dict:
        """创建并立即执行一个任务"""
        if task_id is None:
            task_id = task_queue.push(task_type, description, metadata)

        chunk_callback = on_chunk
        if stream_to_db:
            def chunk_callback(event):
                chunk_type = event.get("type", "chunk")
                insert_chunk(task_id, chunk_type, event)
                if on_chunk:
                    on_chunk(event)

        task = {
            "id": task_id,
            "type": task_type,
            "description": description,
            "metadata": metadata or {},
        }
        try:
            return self.dispatch(task, on_chunk=chunk_callback)
        except GateFailedError as exc:
            # dispatch 已经记录了失败状态，这里只负责向上透传
            if stream_to_db:
                insert_chunk(task_id, "error", {"type": "gate_fail", "message": str(exc)})
            raise
        except Exception as exc:
            task_queue.fail(task_id, str(exc))
            if stream_to_db:
                insert_chunk(task_id, "error", {"type": "error", "message": str(exc)})
            raise

    def run_pending(self, task_type: str = None) -> list[dict]:
        """从队列取出所有 pending 任务并执行"""
        results = []
        while True:
            task = task_queue.pop(task_type)
            if task is None:
                break
            try:
                result = self.dispatch(task)
                results.append(result)
            except Exception as e:
                task_queue.fail(task["id"], str(e))
                print(f"[Orchestrator] 任务失败 {task['id']}: {e}")
        return results

    def status(self) -> str:
        return task_queue.summary()
