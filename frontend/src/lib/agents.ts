export type Layer =
  | "perception"
  | "judgment"
  | "generation"
  | "validation"
  | "exchange"
  | "governance";

export const LAYERS: { id: Layer; label: string; desc: string }[] = [
  { id: "perception", label: "感知层", desc: "感知需求与内部状态" },
  { id: "judgment", label: "判断层", desc: "系统中枢 · 定义标准与优先级" },
  { id: "generation", label: "生成层", desc: "把判断转化为具体产出" },
  { id: "validation", label: "验证层", desc: "PASS / FAIL 把关，失败阻断下游" },
  { id: "exchange", label: "交换层", desc: "把产出转化为外部价值交换" },
  { id: "governance", label: "治理层", desc: "维持系统状态与秩序" },
];

export const AGENTS = [
  {
    task_type: "requirements_analysis",
    icon: "RA",
    name: "需求分析",
    desc: "拆解需求，输出任务清单",
    prompt: "拆解这条需求，输出用户故事、验收标准和优先级。",
    layer: "perception" as Layer,
    isGate: false,
  },
  {
    task_type: "summarize",
    icon: "SU",
    name: "内容汇总",
    desc: "汇总产出，生成状态摘要",
    prompt: "汇总近期 Agent 产出，生成执行摘要、关键发现和待跟进事项。",
    layer: "perception" as Layer,
    isGate: false,
  },
  {
    task_type: "judgment",
    icon: "JD",
    name: "判断中枢",
    desc: "决定优先级，定义'够好'标准，写入决策记录",
    prompt:
      "读取当前系统状态和感知层输出，判断最优先的问题，选定方向，定义验收标准，推送任务。",
    layer: "judgment" as Layer,
    isGate: false,
  },
  {
    task_type: "doc_refactor",
    icon: "DR",
    name: "文档重构",
    desc: "重写文档，使其清晰可执行",
    prompt: "重构指定文档，保留事实，提升结构和可执行性。",
    layer: "generation" as Layer,
    isGate: false,
  },
  {
    task_type: "product_page",
    icon: "PP",
    name: "产品页面",
    desc: "生成产品描述和卖点文案",
    prompt: "基于产品信息生成页面文案，包含标题、卖点和行动按钮。",
    layer: "generation" as Layer,
    isGate: false,
  },
  {
    task_type: "code_scan",
    icon: "CS",
    name: "代码扫描",
    desc: "扫描代码，输出 PASS / FAIL 判决",
    prompt: "扫描当前代码库，找出最高优先级的问题，输出最终判决。",
    layer: "validation" as Layer,
    isGate: true,
  },
  {
    task_type: "test",
    icon: "QA",
    name: "测试验证",
    desc: "设计测试用例，输出 PASS / FAIL 判决",
    prompt: "根据当前需求和实现，设计测试用例，执行验证，输出最终判决。",
    layer: "validation" as Layer,
    isGate: true,
  },
  {
    task_type: "sales",
    icon: "SA",
    name: "销售助手",
    desc: "生成销售话术和跟进策略",
    prompt: "整理销售材料，输出客户可理解的方案、价值和下一步。",
    layer: "exchange" as Layer,
    isGate: false,
  },
  {
    task_type: "task_tracking",
    icon: "TT",
    name: "任务追踪",
    desc: "扫描队列，更新系统状态",
    prompt: "扫描当前任务队列，更新 STATE.json，生成今日优先级报告。",
    layer: "governance" as Layer,
    isGate: false,
  },
] as const;

export type AgentTaskType = (typeof AGENTS)[number]["task_type"];

export const AGENT_BY_TYPE = Object.fromEntries(
  AGENTS.map((agent) => [agent.task_type, agent]),
) as Record<AgentTaskType, (typeof AGENTS)[number]>;

export const AGENTS_BY_LAYER = LAYERS.map((layer) => ({
  ...layer,
  agents: AGENTS.filter((agent) => agent.layer === layer.id),
}));
