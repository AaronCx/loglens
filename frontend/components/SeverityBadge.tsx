import { Severity } from "@/lib/types";

const CONFIG: Record<Severity, { label: string; classes: string }> = {
  info: { label: "Info", classes: "bg-blue-950 text-blue-300 border border-blue-800" },
  warning: { label: "Warning", classes: "bg-yellow-950 text-yellow-300 border border-yellow-800" },
  error: { label: "Error", classes: "bg-orange-950 text-orange-300 border border-orange-800" },
  critical: { label: "Critical", classes: "bg-red-950 text-red-300 border border-red-800" },
};

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const { label, classes } = CONFIG[severity] ?? CONFIG.info;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${classes}`}>
      {label}
    </span>
  );
}
