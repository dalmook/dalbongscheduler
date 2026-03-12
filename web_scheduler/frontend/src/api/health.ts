import { request } from "./client";
import type { HealthResponse } from "../types/common";

export function getHealth() {
  return request<HealthResponse>("/health");
}
