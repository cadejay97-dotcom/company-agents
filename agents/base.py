"""
BaseAgent — 所有专业 Agent 的基类
- DeepSeek API（OpenAI 兼容接口）
- 流式输出
- 工具调用循环
- 自动写入输出到 workspace/outputs/{agent_name}/
"""

import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

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


def _to_openai_tools(tool_defs: list) -> list:
    """将 Anthropic 格式工具定义转换为 OpenAI 格式"""
    result = []
    for t in tool_defs:
        result.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        })
    return result


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
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
        self._raw_tools = TOOL_DEFINITIONS + self.extra_tools
        self.tools = _to_openai_tools(self._raw_tools)
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
            text, tool_calls, finish_reason = self._call_api(messages, on_chunk=on_chunk)

            if text:
                final_output = text

            if finish_reason == "stop":
                break

            if finish_reason == "tool_calls" and tool_calls:
                # 把 assistant 这一轮加入历史
                messages.append({
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                        for tc in tool_calls
                    ],
                })
                # 执行工具，把结果加入历史
                for tc in tool_calls:
                    result_text = self._execute_one_tool(tc["name"], tc["arguments"], on_chunk=on_chunk)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_text,
                    })
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

    def _call_api(self, messages: list, on_chunk=None) -> tuple[str, list, str]:
        """
        调用 DeepSeek API，流式收集响应。
        返回 (text, tool_calls, finish_reason)
        tool_calls: [{"id": ..., "name": ..., "arguments": ...}]
        """
        system_messages = [{"role": "system", "content": self.role}]

        stream = self.client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=8000,
            messages=system_messages + messages,
            tools=self.tools if self.tools else None,
            tool_choice="auto" if self.tools else None,
            stream=True,
        )

        text = ""
        tool_calls_raw: dict[int, dict] = {}
        finish_reason = "stop"

        for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta.content:
                text += delta.content
                if on_chunk:
                    on_chunk({"type": "chunk", "text": delta.content})

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_raw:
                        tool_calls_raw[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_raw[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls_raw[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls_raw[idx]["arguments"] += tc.function.arguments

        tool_calls = [tool_calls_raw[i] for i in sorted(tool_calls_raw)]
        return text, tool_calls, finish_reason

    def _execute_one_tool(self, name: str, arguments: str, on_chunk=None) -> str:
        """执行单个工具调用，返回结果字符串"""
        fn = self.registry.get(name)
        if fn is None:
            result = f"[错误] 未知工具: {name}"
        else:
            try:
                kwargs = json.loads(arguments) if arguments else {}
                result = str(fn(**kwargs))
            except Exception as e:
                result = f"[工具执行错误] {name}: {e}"

        print(f"  → 工具: {name} → {result[:80]}")
        if on_chunk:
            on_chunk({"type": "tool", "name": name, "result": result[:200]})
        return result

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
