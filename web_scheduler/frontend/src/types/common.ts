export interface ApiError {
  detail?: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  db: string;
}
