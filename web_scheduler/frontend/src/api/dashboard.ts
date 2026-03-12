import type { DashboardHtmlResult, DashboardJob, DashboardSummary } from "../types/dashboard";
import { request } from "./client";

export function getDashboardSummary() {
  return request<DashboardSummary>("/dashboard/summary");
}

export function getDashboardJobs() {
  return request<DashboardJob[]>("/dashboard/jobs");
}

export function getDashboardHtmlResults() {
  return request<DashboardHtmlResult[]>("/dashboard/html-results");
}
