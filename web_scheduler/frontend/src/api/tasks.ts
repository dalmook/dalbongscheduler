import type { Artifact } from "../types/artifact";
import type { Run } from "../types/run";
import type { Task, TaskCreatePayload, TaskUpdatePayload } from "../types/task";
import { request } from "./client";

export function listTasks(params?: { name?: string; task_type?: string; is_enabled?: string }) {
  const q = new URLSearchParams();
  if (params?.name) q.set("name", params.name);
  if (params?.task_type) q.set("task_type", params.task_type);
  if (params?.is_enabled) q.set("is_enabled", params.is_enabled);
  const qs = q.toString();
  return request<Task[]>(`/tasks${qs ? `?${qs}` : ""}`);
}

export function getTask(taskId: number) {
  return request<Task>(`/tasks/${taskId}?include_recent_runs=true`);
}

export function createTask(payload: TaskCreatePayload) {
  return request<Task>("/tasks", "POST", payload);
}

export function updateTask(taskId: number, payload: TaskUpdatePayload) {
  return request<Task>(`/tasks/${taskId}`, "PUT", payload);
}

export function removeTask(taskId: number) {
  return request<{ message: string }>(`/tasks/${taskId}`, "DELETE");
}

export function runTask(taskId: number) {
  return request<{ task_id: number; run_id: number; status: string; message: string }>(`/tasks/${taskId}/run`, "POST");
}

export function listTaskRuns(taskId: number) {
  return request<Run[]>(`/tasks/${taskId}/runs`);
}

export function listTaskArtifacts(taskId: number) {
  return request<Artifact[]>(`/tasks/${taskId}/artifacts`);
}
