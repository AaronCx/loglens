import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchEvents, fetchStats, fetchTimeSeries } from "@/lib/api";

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe("fetchEvents", () => {
  it("fetches events with default params", async () => {
    const mockResponse = {
      events: [{ id: "1", severity: "error", service: "svc", message: "msg" }],
      total: 1,
      page: 1,
      page_size: 50,
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await fetchEvents();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/events"),
      expect.objectContaining({ cache: "no-store" })
    );
    expect(result.total).toBe(1);
  });

  it("includes severity filter in query string", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ events: [], total: 0, page: 1, page_size: 50 }),
    });

    await fetchEvents({ severity: ["error", "critical"] });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("severity=error");
    expect(url).toContain("severity=critical");
  });

  it("includes search in query string", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ events: [], total: 0, page: 1, page_size: 50 }),
    });

    await fetchEvents({ search: "timeout" });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("search=timeout");
  });

  it("includes pagination params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ events: [], total: 0, page: 2, page_size: 10 }),
    });

    await fetchEvents({ page: 2, pageSize: 10 });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=10");
  });

  it("throws on API error", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    await expect(fetchEvents()).rejects.toThrow("API error 500");
  });
});

describe("fetchStats", () => {
  it("fetches stats", async () => {
    const mockStats = {
      total: 100,
      by_severity: { error: 50, warning: 30 },
      by_service: { auth: 40 },
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStats),
    });

    const result = await fetchStats();
    expect(result.total).toBe(100);
    expect(result.by_severity.error).toBe(50);
  });
});

describe("fetchTimeSeries", () => {
  it("fetches timeseries with default hours", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await fetchTimeSeries();
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("hours=24");
  });

  it("fetches timeseries with custom hours", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await fetchTimeSeries(48);
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("hours=48");
  });
});
