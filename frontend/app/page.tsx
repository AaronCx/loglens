"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { formatDistanceToNow } from "date-fns";
import {
  AlertTriangle,
  AlertCircle,
  Zap,
  RefreshCw,
  Activity,
  Filter,
  X,
  Search,
} from "lucide-react";

import SeverityBadge from "@/components/SeverityBadge";
import StackTraceViewer from "@/components/StackTraceViewer";
import ErrorsOverTimeChart from "@/components/ErrorsOverTimeChart";
import ErrorsByServiceChart from "@/components/ErrorsByServiceChart";
import StatsCard from "@/components/StatsCard";
import ToastContainer, { ToastMessage, createToast } from "@/components/Toast";
import { Event, Severity, Stats } from "@/lib/types";
import { fetchEvents, fetchStats, deleteEvent } from "@/lib/api";

const SEVERITY_LABELS: Record<Severity, string> = {
  info: "Info",
  warning: "Warning",
  error: "Error",
  critical: "Critical",
};

const SEVERITY_ORDER: Severity[] = ["critical", "error", "warning", "info"];

export default function Dashboard() {
  const [events, setEvents] = useState<Event[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [activeSeverities, setActiveSeverities] = useState<Set<Severity>>(new Set());
  const [environment, setEnvironment] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [liveCount, setLiveCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const addToast = useCallback((type: ToastMessage["type"], message: string) => {
    setToasts((prev) => [...prev.slice(-4), createToast(type, message)]);
  }, []);
  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const PAGE_SIZE = 50;
  const API_URL = "/api";

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(search), 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      const severityList = activeSeverities.size > 0 ? Array.from(activeSeverities) : undefined;
      const result = await fetchEvents({
        severity: severityList,
        search: debouncedSearch || undefined,
        environment: environment || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      setEvents(result.events);
      setTotal(result.total);
    } catch {
      addToast("error", "Failed to load events. Check your connection.");
    } finally {
      setLoading(false);
    }
  }, [activeSeverities, debouncedSearch, environment, page, addToast]);

  const loadStats = useCallback(async () => {
    try {
      const s = await fetchStats();
      setStats(s);
    } catch {
      addToast("error", "Failed to load stats.");
    }
  }, [addToast]);

  useEffect(() => { loadEvents(); loadStats(); }, [loadEvents, loadStats]);

  useEffect(() => {
    const es = new EventSource(`${API_URL}/stream`);
    es.onopen = () => setIsConnected(true);
    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "event") {
          const newEvent: Event = msg.data;
          setLiveCount((c) => c + 1);
          setEvents((prev) => {
            if (activeSeverities.size > 0 && !activeSeverities.has(newEvent.severity)) return prev;
            return [newEvent, ...prev.slice(0, PAGE_SIZE - 1)];
          });
          setTotal((t) => t + 1);
          loadStats();
        }
      } catch { /* ignore parse errors */ }
    };
    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        addToast("warning", "Live connection lost. Click Refresh to reconnect.");
      }
      setIsConnected(false);
    };
    return () => { es.close(); setIsConnected(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [API_URL]);

  const toggleSeverity = (sev: Severity) => {
    setActiveSeverities((prev) => {
      const next = new Set(prev);
      if (next.has(sev)) next.delete(sev); else next.add(sev);
      return next;
    });
    setPage(1);
  };

  const clearFilters = () => { setActiveSeverities(new Set()); setSearch(""); setEnvironment(""); setPage(1); };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const hasFilters = activeSeverities.size > 0 || debouncedSearch || environment;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 bg-gray-900 px-6 py-4 sticky top-0 z-40">
        <div className="mx-auto max-w-screen-2xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">LogLens</h1>
              <p className="text-xs text-gray-400">Error Monitoring Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 text-sm ${isConnected ? "text-green-400" : "text-gray-500"}`}>
              <span className={`h-2 w-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
              {isConnected ? "Live" : "Connecting…"}
            </div>
            {liveCount > 0 && (
              <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-medium">+{liveCount} live</span>
            )}
            <button
              onClick={() => { loadEvents(); loadStats(); }}
              className="flex items-center gap-1.5 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm hover:bg-gray-700 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-screen-2xl px-6 py-6 space-y-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatsCard label="Total Events" value={stats?.total ?? 0} icon={<Activity className="h-5 w-5" />} color="indigo" />
          <StatsCard label="Critical" value={stats?.by_severity?.critical ?? 0} icon={<Zap className="h-5 w-5" />} color="red" />
          <StatsCard label="Errors" value={stats?.by_severity?.error ?? 0} icon={<AlertCircle className="h-5 w-5" />} color="orange" />
          <StatsCard label="Warnings" value={stats?.by_severity?.warning ?? 0} icon={<AlertTriangle className="h-5 w-5" />} color="yellow" />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2 rounded-xl border border-gray-800 bg-gray-900 p-4">
            <h2 className="mb-4 text-sm font-semibold text-gray-300">Events Over Time (24h)</h2>
            <ErrorsOverTimeChart />
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
            <h2 className="mb-4 text-sm font-semibold text-gray-300">Events by Service</h2>
            <ErrorsByServiceChart stats={stats} />
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Filter className="h-4 w-4" />
              <span>Severity:</span>
            </div>
            {SEVERITY_ORDER.map((sev) => (
              <button
                key={sev}
                onClick={() => toggleSeverity(sev)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-all border ${
                  activeSeverities.has(sev) ? severityActiveClass(sev) : "border-gray-700 text-gray-400 hover:border-gray-500"
                }`}
              >
                {SEVERITY_LABELS[sev]}
                {stats?.by_severity?.[sev] !== undefined && (
                  <span className="ml-1.5 opacity-70">({stats.by_severity[sev]})</span>
                )}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-2">
              <select
                value={environment}
                onChange={(e) => { setEnvironment(e.target.value); setPage(1); }}
                className="rounded-md border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Envs</option>
                <option value="production">Production</option>
                <option value="staging">Staging</option>
                <option value="development">Development</option>
                <option value="testing">Testing</option>
              </select>
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search messages…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="rounded-md border border-gray-700 bg-gray-800 pl-8 pr-3 py-1.5 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 w-48"
                />
              </div>
              {hasFilters && (
                <button onClick={clearFilters} className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors">
                  <X className="h-3.5 w-3.5" />
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
          <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
            <h2 className="text-sm font-semibold text-gray-300">
              Events
              <span className="ml-2 text-xs text-gray-500">{total.toLocaleString()} total</span>
            </h2>
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-gray-500" />}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3 text-left w-28">Severity</th>
                  <th className="px-4 py-3 text-left w-32">Service</th>
                  <th className="px-4 py-3 text-left">Message</th>
                  <th className="px-4 py-3 text-left w-24">Env</th>
                  <th className="px-4 py-3 text-right w-36">Time</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 && !loading && (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center text-gray-500">No events found</td>
                  </tr>
                )}
                {events.map((event) => (
                  <tr
                    key={event.id}
                    onClick={() => setSelectedEvent(selectedEvent?.id === event.id ? null : event)}
                    className={`border-b border-gray-800/50 cursor-pointer transition-colors ${
                      selectedEvent?.id === event.id ? "bg-indigo-950/40" : "hover:bg-gray-800/50"
                    }`}
                  >
                    <td className="px-4 py-3"><SeverityBadge severity={event.severity} /></td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-indigo-300">{event.service}</span>
                    </td>
                    <td className="px-4 py-3 max-w-0">
                      <p className="truncate text-gray-200">{event.message}</p>
                      {event.stack_trace && <span className="text-xs text-gray-500">Has stack trace</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded px-1.5 py-0.5 text-xs bg-gray-800 text-gray-400">
                        {event.environment || "prod"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-gray-500">
                      {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-gray-800 px-4 py-3 text-sm text-gray-400">
              <span>Page {page} of {totalPages}</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded px-3 py-1 border border-gray-700 disabled:opacity-40 hover:bg-gray-800 transition-colors"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="rounded px-3 py-1 border border-gray-700 disabled:opacity-40 hover:bg-gray-800 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {selectedEvent && (
        <StackTraceViewer
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onDelete={async (eventId) => {
            const apiKey = prompt("Enter API key to delete this event:");
            if (!apiKey) return;
            try {
              await deleteEvent(eventId, apiKey);
              setSelectedEvent(null);
              setEvents((prev) => prev.filter((e) => e.id !== eventId));
              setTotal((t) => Math.max(0, t - 1));
              loadStats();
              addToast("success", "Event deleted successfully.");
            } catch {
              addToast("error", "Failed to delete event. Check your API key.");
            }
          }}
        />
      )}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

function severityActiveClass(sev: Severity): string {
  const map: Record<Severity, string> = {
    info: "border-blue-500 bg-blue-950 text-blue-300",
    warning: "border-yellow-500 bg-yellow-950 text-yellow-300",
    error: "border-orange-500 bg-orange-950 text-orange-300",
    critical: "border-red-500 bg-red-950 text-red-300",
  };
  return map[sev];
}
