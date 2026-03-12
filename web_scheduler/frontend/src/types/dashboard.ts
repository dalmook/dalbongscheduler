export interface DashboardNextScheduledRun {
  task_id: number;
  task_name: string;
  schedule_type: string;
  next_run_at?: string | null;
}

export interface DashboardRecentFailedRun {
  run_id: number;
  task_id: number;
  task_name: string;
  error_message?: string | null;
  finished_at?: string | null;
}

export interface DashboardSummary {
  total_tasks: number;
  enabled_tasks: number;
  manual_tasks: number;
  scheduled_tasks: number;
  running_tasks: number;
  success_runs_24h: number;
  failed_runs_24h: number;
  html_artifacts_24h: number;
  next_scheduled_runs: DashboardNextScheduledRun[];
  recent_failed_runs: DashboardRecentFailedRun[];
}

export interface DashboardJob {
  job_id: string;
  task_id?: number | null;
  task_name?: string | null;
  trigger: string;
  next_run_time?: string | null;
  is_enabled: boolean;
}

export interface DashboardHtmlResult {
  task_id: number;
  task_name: string;
  latest_run_status?: string | null;
  latest_artifact_id?: number | null;
  latest_generated_at?: string | null;
  preview_text?: string | null;
  has_error: boolean;
  last_success_at?: string | null;
  last_failed_at?: string | null;
}
