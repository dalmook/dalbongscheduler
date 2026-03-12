import type { Run } from "../types/run";
import { request } from "./client";

export function listRuns(params?: { task_id?: string; status?: string; trigger_type?: string }) {
  const q = new URLSearchParams();
  if (params?.task_id) q.set("task_id", params.task_id);
  if (params?.status) q.set("status", params.status);
  if (params?.trigger_type) q.set("trigger_type", params.trigger_type);
  const qs = q.toString();
  return request<Run[]>(`/runs${qs ? `?${qs}` : ""}`);
}

export function getRun(runId: number) {
  return request<Run>(`/runs/${runId}`);
}
