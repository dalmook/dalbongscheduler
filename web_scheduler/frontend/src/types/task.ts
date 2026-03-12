export type TaskType = "python" | "sql" | "html";
export type ScheduleType = "manual" | "cron" | "interval";

export interface Task {
  id: number;
  name: string;
  description?: string | null;
  task_type: TaskType;
  schedule_type: ScheduleType;
  cron_expr?: string | null;
  interval_seconds?: number | null;
  is_enabled: boolean;
  timezone?: string | null;
  next_run_at?: string | null;
  scheduler_job_id?: string | null;
  python_code?: string | null;
  sql_code?: string | null;
  html_template?: string | null;
  params_json?: string | null;
  output_format?: string | null;
  last_run_status?: string | null;
  last_run_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskCreatePayload {
  name: string;
  description?: string;
  task_type: TaskType;
  schedule_type: ScheduleType;
  cron_expr?: string;
  interval_seconds?: number;
  is_enabled: boolean;
  timezone?: string;
  python_code?: string;
  sql_code?: string;
  html_template?: string;
  params_json?: string;
  output_format?: string;
}

export type TaskUpdatePayload = Partial<TaskCreatePayload>;
