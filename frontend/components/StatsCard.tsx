import { ReactNode } from "react";

const COLOR_MAP = {
  indigo: "text-indigo-400 bg-indigo-900/30",
  red: "text-red-400 bg-red-900/30",
  orange: "text-orange-400 bg-orange-900/30",
  yellow: "text-yellow-400 bg-yellow-900/30",
  green: "text-green-400 bg-green-900/30",
};

interface StatsCardProps {
  label: string;
  value: number;
  icon: ReactNode;
  color: keyof typeof COLOR_MAP;
}

export default function StatsCard({ label, value, icon, color }: StatsCardProps) {
  const colorClass = COLOR_MAP[color] ?? COLOR_MAP.indigo;
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">{label}</p>
        <div className={`rounded-lg p-2 ${colorClass}`}>{icon}</div>
      </div>
      <p className="mt-2 text-2xl font-bold tabular-nums">{value.toLocaleString()}</p>
    </div>
  );
}
