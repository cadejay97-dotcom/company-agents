"""
BaseAgent — 所有专业 Agent 的基类
- 提示词缓存 (system prompt cache)
- 流式输出
- 工具调用循环
- 自动写入输出到 workspace/outputs/{agent_name}/
"""

import anthropic
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from datetime import datetime
from core.tools import TOOL_DEFINITIONS, TOOL_REGISTRY

WORKSPACE = Path(__file__).parent.parent / "workspace"
_STATE_FILE = WORKSPACE / "STATE.json"


def _load_state() -> str:
    """读取单一事实源，注入每个 Agent 的上下文。"""
    if not _STATE_FILE.exists():
        return ""
    try:
        state = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        return (
            f"当前目标: {state.get('current_goal', '未定义')}\n"
            f"当前阶段: {state.get('phase', '未定义')}\n"
            f"约束条件: {'; '.join(state.get('constraints', []))}\n"
            f"阻塞项: {'; '.join(state.get('blockers', [])) or '无'}"
        )
    except Exception:
        return ""


class BaseAgent:
    """
    继承此类，只需提供：
      name        : Agent 唯一标识（用于输出目录）
      role        : system prompt（定义职责、工作方式、输出格式）
      extra_tools : 额外的工具定义（可选，追加到公共工具集）
      extra_registry : 额外工具的实现 dict（可选）
    """

    name: str = "base_agent"
    role: str = "你是一个通用助手。"
    extra_tools: list = []
    extra_registry: dict = {}

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.tools = TOOL_DEFINITIONS + self.extra_tools
        self.registry = {**TOOL_REGISTRY, **self.extra_registry}
        self._output_dir = WORKSPACE / "outputs" / self.name
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ── 主入口 ────────────────────────────────────────────────────────────────

    def run(self, task: dict, on_chunk=None) -> dict:
        """
        执行一个任务。
        task     : { id, type, description, metadata }
        on_chunk : 可选回调 fn(event_dict)，供 Web 层实时推送
        返回     : { agent, task_id, output, saved_to }
        """
        print(f"\n[{self.name}] 开始任务: {task['description'][:60]}")
        if on_chunk:
            on_chunk({"type": "start", "agent": self.name})

        messages = [{"role": "user", "content": self._build_prompt(task)}]
        final_output = ""

        for step in range(20):  # 最多 20 轮工具调用
            response = self._call_api(messages, on_chunk=on_chunk)

            text_blocks = [b.text for b in response.content if b.type == "text"]
            if text_blocks:
                final_output = "\n".join(text_blocks)

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = self._execute_tools(response.content, on_chunk=on_chunk)
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        saved_to = self._save_output(task, final_output)
        verdict = self._extract_verdict(final_output)
        layer = getattr(self.__class__, "layer", None)

        print(f"[{self.name}] 完成" + (f" — 判决: {verdict}" if verdict else ""))
        if on_chunk:
            on_chunk({"type": "done", "verdict": verdict})

        return {
            "agent": self.name,
            "layer": layer,
            "task_id": task.get("id", "unknown"),
            "output": final_output,
            "saved_to": str(saved_to),
            "verdict": verdict,
        }

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    def _build_prompt(self, task: dict) -> str:
        lines = []
        state_ctx = _load_state()
        if state_ctx:
            lines.append(f"## 系统状态\n{state_ctx}")
        lines += [
            f"任务ID: {task.get('id', 'N/A')}",
            f"任务类型: {task.get('type', 'N/A')}",
            f"任务描述:\n{task['description']}",
        ]
        if task.get("metadata"):
            lines.append(f"附加信息:\n{task['metadata']}")
        return "\n\n".join(lines)

    def _extract_verdict(self, output: str) -> str | None:
        """从输出中提取结构化判决。验证层 Agent 必须在输出末尾写 VERDICT: PASS 或 VERDICT: FAIL。"""
        for line in reversed(output.strip().splitlines()):
            line = line.strip().upper()
            if line.startswith("VERDICT:"):
                verdict = line.split(":", 1)[1].strip()
                if verdict in ("PASS", "FAIL"):
                    return verdict.lower()
        return None

    def _call_api(self, messages: list, on_chunk=None) -> anthropic.types.Message:
        """调用 API，带提示词缓存 + 流式推送"""
        with self.client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": self.role,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=self.tools,
            messages=messages,
        ) as stream:
            for event in stream:
                if (on_chunk
                        and event.type == "content_block_delta"
                        and hasattr(event.delta, "text")):
                    on_chunk({"type": "chunk", "text": event.delta.text})
            return stream.get_final_message()

    def _execute_tools(self, content_blocks, on_chunk=None) -> list[dict]:
        """执行所有 tool_use block，返回 tool_result list"""
        results = []
        for block in content_blocks:
            if block.type != "tool_use":
                continue
            fn = self.registry.get(block.name)
            if fn is None:
                result_text = f"[错误] 未知工具: {block.name}"
            else:
                try:
                    result_text = str(fn(**block.input))
                except Exception as e:
                    result_text = f"[工具执行错误] {block.name}: {e}"

            print(f"  → 工具: {block.name} → {result_text[:80]}")
            if on_chunk:
                on_chunk({"type": "tool", "name": block.name,
                          "input": block.input, "result": result_text[:200]})
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })
        return results

    def _save_output(self, task: dict, output: str) -> Path:
        """将输出保存到 workspace/outputs/{agent_name}/{task_id}.md"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_id = task.get("id", "unknown")
        filename = f"{task_id}_{ts}.md"
        path = self._output_dir / filename
        content = f"# 任务输出: {task.get('type', '')}\n\n"
        content += f"**描述**: {task['description']}\n\n---\n\n{output}"
        path.write_text(content, encoding="utf-8")
        return path
