export interface Artifact {
  id: number;
  task_id: number;
  run_id: number;
  artifact_type: "html" | "json" | "text" | "csv";
  content_text?: string | null;
  content_html?: string | null;
  content_json?: string | null;
  is_latest: boolean;
  version_no: number;
  created_at: string;
}
