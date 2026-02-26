export type Severity = "info" | "warning" | "error" | "critical";

export interface Event {
  id: string;
  timestamp: string;
  severity: Severity;
  service: string;
  message: string;
  stack_trace: string | null;
  metadata: Record<string, unknown> | null;
  environment: string | null;
}

export interface EventsListResponse {
  events: Event[];
  total: number;
  page: number;
  page_size: number;
}

export interface Stats {
  total: number;
  by_severity: Record<string, number>;
  by_service: Record<string, number>;
}

export interface TimeSeriesPoint {
  time: string;
  info: number;
  warning: number;
  error: number;
  critical: number;
}
