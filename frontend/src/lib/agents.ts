export const AGENTS = [
  {
    task_type: "code_scan",
    icon: "CS",
    name: "代码扫描",
    desc: "扫描代码变更，识别风险点",
    prompt: "扫描当前代码库，找出最高优先级的问题和修复建议。",
  },
  {
    task_type: "doc_refactor",
    icon: "DR",
    name: "文档重构",
    desc: "重写文档，使其清晰易读",
    prompt: "重构指定文档，保留事实，提升结构和可执行性。",
  },
  {
    task_type: "sales",
    icon: "SA",
    name: "销售助手",
    desc: "生成销售话术和跟进策略",
    prompt: "整理销售材料，输出客户可理解的方案、价值和下一步。",
  },
  {
    task_type: "requirements_analysis",
    icon: "RA",
    name: "需求分析",
    desc: "拆解需求，输出任务清单",
    prompt: "拆解这条需求，输出用户故事、验收标准和优先级。",
  },
  {
    task_type: "product_page",
    icon: "PP",
    name: "产品页面",
    desc: "生成产品描述和卖点文案",
    prompt: "基于产品信息生成页面文案，包含标题、卖点和行动按钮。",
  },
  {
    task_type: "summarize",
    icon: "SU",
    name: "内容汇总",
    desc: "汇总产出，生成周报",
    prompt: "汇总近期 Agent 产出，生成执行摘要、关键发现和待跟进事项。",
  },
  {
    task_type: "test",
    icon: "QA",
    name: "测试用例",
    desc: "生成测试用例和验证流程",
    prompt: "根据当前需求和实现，设计测试用例、边界条件和验证步骤。",
  },
  {
    task_type: "task_tracking",
    icon: "TT",
    name: "任务追踪",
    desc: "扫描队列，生成优先级报告",
    prompt: "扫描当前任务队列，生成今日优先级报告。",
  },
] as const;

export type AgentTaskType = (typeof AGENTS)[number]["task_type"];

export const AGENT_BY_TYPE = Object.fromEntries(
  AGENTS.map((agent) => [agent.task_type, agent]),
) as Record<AgentTaskType, (typeof AGENTS)[number]>;
