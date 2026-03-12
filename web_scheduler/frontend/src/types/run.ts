export interface Run {
  id: number;
  task_id: number;
  trigger_type: "manual" | "scheduled";
  status: "queued" | "running" | "success" | "failed";
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  result_summary?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface RunStartResponse {
  task_id: number;
  run_id: number;
  status: string;
  message: string;
}
