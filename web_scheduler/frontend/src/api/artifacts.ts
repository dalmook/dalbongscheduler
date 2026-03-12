import { API_BASE_URL, apiRequest } from "./client";
import type { Artifact, ArtifactListItem } from "../types/artifact";

export async function fetchArtifacts(params?: { task_id?: string; run_id?: string; is_latest?: string }): Promise<ArtifactListItem[]> {
  const query = new URLSearchParams();
  if (params?.task_id) query.set("task_id", params.task_id);
  if (params?.run_id) query.set("run_id", params.run_id);
  if (params?.is_latest) query.set("is_latest", params.is_latest);
  const qs = query.toString();
  return apiRequest<ArtifactListItem[]>(`/artifacts${qs ? `?${qs}` : ""}`);
}

export async function fetchArtifact(artifactId: number): Promise<Artifact> {
  return apiRequest<Artifact>(`/artifacts/${artifactId}`);
}

export function artifactPreviewUrl(artifactId: number): string {
  return `${API_BASE_URL}/artifacts/${artifactId}/preview`;
}
