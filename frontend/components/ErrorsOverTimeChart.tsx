"use client";

import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";
import { fetchTimeSeries } from "@/lib/api";
import { TimeSeriesPoint } from "@/lib/types";

const COLORS = {
  critical: "#ef4444",
  error: "#f97316",
  warning: "#eab308",
  info: "#3b82f6",
};

export default function ErrorsOverTimeChart() {
  const [data, setData] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const points = await fetchTimeSeries(24);
        setData(points);
      } catch (err) {
        console.error("Failed to load timeseries:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-gray-500">
        Loading chart…
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-gray-500">
        No data yet — send some events!
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    label: format(new Date(d.time), "HH:mm"),
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={formatted} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <defs>
          {(Object.entries(COLORS) as [string, string][]).map(([key, color]) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="label" tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} />
        <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
          labelStyle={{ color: "#9ca3af", marginBottom: 4 }}
          itemStyle={{ color: "#e5e7eb" }}
        />
        <Legend wrapperStyle={{ paddingTop: 8, fontSize: 12 }} />
        {(["critical", "error", "warning", "info"] as const).map((sev) => (
          <Area
            key={sev}
            type="monotone"
            dataKey={sev}
            stroke={COLORS[sev]}
            fill={`url(#grad-${sev})`}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
