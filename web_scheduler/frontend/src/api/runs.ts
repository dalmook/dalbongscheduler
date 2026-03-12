import { apiRequest } from "./client";
import type { Run } from "../types/run";

export async function fetchRuns(params?: { task_id?: string; status?: string; trigger_type?: string }): Promise<Run[]> {
  const query = new URLSearchParams();
  if (params?.task_id) query.set("task_id", params.task_id);
  if (params?.status) query.set("status", params.status);
  if (params?.trigger_type) query.set("trigger_type", params.trigger_type);
  const qs = query.toString();
  return apiRequest<Run[]>(`/runs${qs ? `?${qs}` : ""}`);
}

export async function fetchRun(runId: number): Promise<Run> {
  return apiRequest<Run>(`/runs/${runId}`);
}
