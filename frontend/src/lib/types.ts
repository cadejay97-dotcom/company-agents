export interface Task {
  id: string;
  type: string;
  description: string;
  status: "pending" | "running" | "done" | "failed" | string;
  agent?: string | null;
  output?: string | null;
  metadata?: Record<string, unknown>;
  created_at?: string;
  completed_at?: string | null;
}

export interface TriggerSchedule {
  name?: string;
  cron?: string;
  task_type?: string;
  description?: string;
}

export interface TriggerWebhook {
  name?: string;
  path?: string;
  task_type?: string;
}
