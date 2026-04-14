"""
入口 — 演示如何使用 Orchestrator 驱动 Agent 飞轮

用法：
  python main.py                  # 运行示例演示
  python main.py --agent tracker  # 只运行任务追踪 Agent
  python main.py --pending        # 执行队列中所有待处理任务
"""

import argparse
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import Orchestrator
from core import task_queue


def demo():
    """最小闭环演示：推入任务 → 需求拆解 → 任务追踪"""
    orch = Orchestrator()

    print("=" * 60)
    print("公司智能体飞轮 — 演示模式")
    print("=" * 60)

    # 1. 需求拆解
    print("\n[步骤 1] 需求拆解 Agent")
    orch.run_task(
        task_type="requirements_analysis",
        description=(
            "用户希望在我们的 SaaS 平台上增加「团队协作」功能，"
            "包括：多人实时编辑、评论、@提及、版本历史。"
            "需要将这个大需求拆解成可开发的子任务，并评估优先级。"
        ),
    )

    # 2. 任务追踪（检视昨天遗留）
    print("\n[步骤 2] 任务追踪 Agent")
    orch.run_task(
        task_type="task_tracking",
        description="扫描当前任务队列，生成未完成任务报告和今日优先级建议。",
    )

    # 3. 汇总
    print("\n[步骤 3] 汇总 Agent")
    orch.run_task(
        task_type="summarize",
        description="汇总今天各 Agent 的产出，生成一份执行摘要报告。",
    )

    print("\n" + "=" * 60)
    print("演示完成。查看 workspace/outputs/ 获取所有产出。")
    print(f"任务队列状态: {orch.status()}")


def run_agent(agent_name: str):
    """直接触发指定 Agent 处理一个任务"""
    orch = Orchestrator()
    descriptions = {
        "tracker":      ("task_tracking", "生成完整的任务追踪报告"),
        "scanner":      ("code_scan",     "扫描 workspace/ 目录下的所有代码文件"),
        "summarizer":   ("summarize",     "汇总所有 Agent 今日产出"),
        "sales":        ("sales",         "整理 workspace/shared/ 下的销售材料"),
    }
    if agent_name not in descriptions:
        print(f"可用: {list(descriptions.keys())}")
        return
    task_type, desc = descriptions[agent_name]
    result = orch.run_task(task_type, desc)
    print(f"\n输出:\n{result['output'][:300]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="公司智能体飞轮")
    parser.add_argument("--agent", help="运行指定 agent: tracker / scanner / summarizer / sales")
    parser.add_argument("--pending", action="store_true", help="执行队列中所有 pending 任务")
    args = parser.parse_args()

    if args.agent:
        run_agent(args.agent)
    elif args.pending:
        orch = Orchestrator()
        results = orch.run_pending()
        print(f"\n完成 {len(results)} 个任务")
    else:
        demo()
