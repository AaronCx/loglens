import { EventsListResponse, Stats, TimeSeriesPoint, Severity } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

interface FetchEventsParams {
  severity?: Severity[];
  search?: string;
  page?: number;
  pageSize?: number;
}

export async function fetchEvents(params: FetchEventsParams = {}): Promise<EventsListResponse> {
  const qs = new URLSearchParams();
  if (params.severity?.length) params.severity.forEach((s) => qs.append("severity", s));
  if (params.search) qs.set("search", params.search);
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("page_size", String(params.pageSize));

  const query = qs.toString() ? `?${qs.toString()}` : "";
  return get<EventsListResponse>(`/events${query}`);
}

export async function fetchStats(): Promise<Stats> {
  return get<Stats>("/stats");
}

export async function fetchTimeSeries(hours = 24): Promise<TimeSeriesPoint[]> {
  return get<TimeSeriesPoint[]>(`/stats/timeseries?hours=${hours}`);
}
