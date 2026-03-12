export interface ArtifactListItem {
  id: number;
  task_id: number;
  run_id: number;
  artifact_type: "html" | "json" | "text" | "csv";
  is_latest: boolean;
  version_no: number;
  created_at: string;
}

export interface Artifact extends ArtifactListItem {
  content_text?: string | null;
  content_html?: string | null;
  content_json?: string | null;
}
