-- 在 Supabase 控制台 → SQL Editor 里执行此文件

-- 任务队列
CREATE TABLE IF NOT EXISTS tasks (
  id          TEXT PRIMARY KEY,
  type        TEXT NOT NULL,
  description TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pending',
  agent       TEXT,
  output      TEXT,
  metadata    JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Agent 流式输出（每个 chunk 一行，前端实时订阅）
CREATE TABLE IF NOT EXISTS task_chunks (
  id         BIGSERIAL PRIMARY KEY,
  task_id    TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  chunk_type TEXT NOT NULL,   -- start | chunk | tool | done | error
  content    JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 开启 Realtime（让前端能实时收到 INSERT 事件）
ALTER TABLE tasks       REPLICA IDENTITY FULL;
ALTER TABLE task_chunks REPLICA IDENTITY FULL;

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.tasks;
EXCEPTION
  WHEN duplicate_object THEN NULL;
  WHEN undefined_object THEN RAISE NOTICE 'supabase_realtime publication not found; enable Realtime from Supabase dashboard';
END $$;

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.task_chunks;
EXCEPTION
  WHEN duplicate_object THEN NULL;
  WHEN undefined_object THEN RAISE NOTICE 'supabase_realtime publication not found; enable Realtime from Supabase dashboard';
END $$;

-- RLS：后端用 service_role key（完全权限），前端用 anon key（只读）
ALTER TABLE tasks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_tasks"   ON tasks       FOR SELECT USING (true);
CREATE POLICY "anon_read_chunks"  ON task_chunks FOR SELECT USING (true);

-- 索引（加速队列查询）
CREATE INDEX IF NOT EXISTS idx_tasks_status    ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_chunks_task_id  ON task_chunks(task_id);
