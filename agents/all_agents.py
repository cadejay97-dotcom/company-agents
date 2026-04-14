"""
向后兼容 shim — 实际实现已迁移至 layers/

新代码请直接从 layers 导入：
  from layers import JudgmentAgent, TesterAgent, ...
"""

from layers import (  # noqa: F401
    RequirementsAnalystAgent,
    SummarizerAgent,
    JudgmentAgent,
    DocRefactorAgent,
    ProductPageAgent,
    CodeScannerAgent,
    TesterAgent,
    SalesAgent,
    TaskTrackerAgent,
)
