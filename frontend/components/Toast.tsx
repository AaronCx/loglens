"use client";

import { useEffect, useState } from "react";
import { X, AlertCircle, CheckCircle, Info, AlertTriangle } from "lucide-react";

export type ToastType = "error" | "success" | "warning" | "info";

export interface ToastMessage {
  id: string;
  type: ToastType;
  message: string;
}

const ICONS: Record<ToastType, typeof AlertCircle> = {
  error: AlertCircle,
  success: CheckCircle,
  warning: AlertTriangle,
  info: Info,
};

const STYLES: Record<ToastType, string> = {
  error: "border-red-800 bg-red-950 text-red-200",
  success: "border-green-800 bg-green-950 text-green-200",
  warning: "border-yellow-800 bg-yellow-950 text-yellow-200",
  info: "border-blue-800 bg-blue-950 text-blue-200",
};

function ToastItem({ toast, onDismiss }: { toast: ToastMessage; onDismiss: (id: string) => void }) {
  const Icon = ICONS[toast.type];

  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 5000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg animate-in slide-in-from-right ${STYLES[toast.type]}`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <p className="text-sm flex-1">{toast.message}</p>
      <button onClick={() => onDismiss(toast.id)} className="shrink-0 opacity-60 hover:opacity-100 transition-opacity">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export default function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

let _counter = 0;
export function createToast(type: ToastType, message: string): ToastMessage {
  return { id: `toast-${++_counter}-${Date.now()}`, type, message };
}
