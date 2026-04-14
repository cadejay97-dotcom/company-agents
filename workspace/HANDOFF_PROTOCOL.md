# Agent 交接协议

> 所有层之间的任务交接必须遵循此格式。
> 没有明确交接结构的任务流转，视为未定义行为。

---

## 标准交接结构

```json
{
  "task_id": "string",
  "from_layer": "perception | judgment | generation | validation | exchange | governance",
  "to_layer": "perception | judgment | generation | validation | exchange | governance",
  "current_task": "string — 本次任务的一句话描述",
  "input_summary": "string — 本层接收到的输入摘要",
  "output_summary": "string — 本层产出的摘要",
  "constraints": ["list — 下游必须遵守的约束"],
  "risks": ["list — 已识别的风险"],
  "next_step": "string — 建议的下一步",
  "requires_approval": true | false,
  "verdict": "pass | fail | pending"
}
```

---

## 各层职责边界

| 层 | 产出 | 不负责 |
|----|------|--------|
| 感知层 | 问题定义、信号、状态摘要 | 最终决策 |
| 判断层 | 优先级、标准、方案选择、决策记录 | 内容生成 |
| 生成层 | 具体方案、内容、代码、文档 | 评判好坏 |
| 验证层 | PASS/FAIL 判决 + 问题清单 | 生成替代方案 |
| 交换层 | 触达、成交、交付、反馈收集 | 内部质量评判 |
| 治理层 | 状态记录、协议执行、权限边界、异常上报 | 业务内容生产 |

---

## Gate 规则

- 验证层返回 `verdict: fail` 时，Orchestrator **必须中止**下游任务
- 验证层返回 `verdict: pass` 时，才可继续流转
- 任何需要人类裁决的决策，必须在 `requires_approval: true` 时暂停并上报

---

## 异常上报

当以下情况发生时，必须写入 `DECISIONS.md` 并设置 `blockers` in `STATE.json`：
- 验证层连续 2 次 FAIL
- 任务超过最大重试次数
- Agent 收到无法处理的指令
- 状态与 STATE.json 不一致

---
