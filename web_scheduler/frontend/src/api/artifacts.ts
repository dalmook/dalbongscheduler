import type { Artifact } from "../types/artifact";
import { API_BASE_URL, request } from "./client";

export function listArtifacts(params?: { task_id?: string; run_id?: string; is_latest?: string }) {
  const q = new URLSearchParams();
  if (params?.task_id) q.set("task_id", params.task_id);
  if (params?.run_id) q.set("run_id", params.run_id);
  if (params?.is_latest) q.set("is_latest", params.is_latest);
  const qs = q.toString();
  return request<Artifact[]>(`/artifacts${qs ? `?${qs}` : ""}`);
}

export function getArtifact(artifactId: number) {
  return request<Artifact>(`/artifacts/${artifactId}`);
}

export function getArtifactPreviewUrl(artifactId: number) {
  return `${API_BASE_URL}/artifacts/${artifactId}/preview`;
}
