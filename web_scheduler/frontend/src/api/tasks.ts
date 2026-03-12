import { apiRequest } from "./client";
import type { Task, TaskCreatePayload, TaskUpdatePayload } from "../types/task";
import type { Run } from "../types/run";
import type { ArtifactListItem } from "../types/artifact";

export async function fetchTasks(params?: { name?: string; task_type?: string; is_enabled?: string }): Promise<Task[]> {
  const query = new URLSearchParams();
  if (params?.name) query.set("name", params.name);
  if (params?.task_type) query.set("task_type", params.task_type);
  if (params?.is_enabled) query.set("is_enabled", params.is_enabled);
  const qs = query.toString();
  return apiRequest<Task[]>(`/tasks${qs ? `?${qs}` : ""}`);
}

export async function fetchTask(taskId: number): Promise<Task> {
  return apiRequest<Task>(`/tasks/${taskId}?include_recent_runs=true`);
}

export async function createTask(payload: TaskCreatePayload): Promise<Task> {
  return apiRequest<Task>("/tasks", "POST", payload);
}

export async function updateTask(taskId: number, payload: TaskUpdatePayload): Promise<Task> {
  return apiRequest<Task>(`/tasks/${taskId}`, "PUT", payload);
}

export async function deleteTask(taskId: number): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/tasks/${taskId}`, "DELETE");
}

export async function runTask(taskId: number): Promise<{ task_id: number; run_id: number; status: string; message: string }> {
  return apiRequest(`/tasks/${taskId}/run`, "POST");
}

export async function fetchTaskRuns(taskId: number): Promise<Run[]> {
  return apiRequest<Run[]>(`/tasks/${taskId}/runs`);
}

export async function fetchTaskArtifacts(taskId: number): Promise<ArtifactListItem[]> {
  return apiRequest<ArtifactListItem[]>(`/tasks/${taskId}/artifacts`);
}
