import { apiRequest } from "./client";
import type { DashboardHtmlResult, DashboardJob, DashboardSummary } from "../types/dashboard";

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>("/dashboard/summary");
}

export async function fetchDashboardJobs(): Promise<DashboardJob[]> {
  return apiRequest<DashboardJob[]>("/dashboard/jobs");
}

export async function fetchDashboardHtmlResults(): Promise<DashboardHtmlResult[]> {
  return apiRequest<DashboardHtmlResult[]>("/dashboard/html-results");
}
