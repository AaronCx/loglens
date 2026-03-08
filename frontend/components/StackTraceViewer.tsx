"use client";

import { X, Copy, Check, Trash2 } from "lucide-react";
import { useState } from "react";
import { format } from "date-fns";
import { Event } from "@/lib/types";
import { deleteEvent } from "@/lib/api";
import SeverityBadge from "./SeverityBadge";

interface Props {
  event: Event;
  onClose: () => void;
  onDelete?: (eventId: string) => void;
}

export default function StackTraceViewer({ event, onClose, onDelete }: Props) {
  const [copied, setCopied] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const copy = async () => {
    const text = [
      `Severity: ${event.severity}`,
      `Service: ${event.service}`,
      `Time: ${event.timestamp}`,
      `Message: ${event.message}`,
      event.stack_trace ? `\nStack Trace:\n${event.stack_trace}` : "",
    ].join("\n");
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Drawer */}
      <div className="fixed bottom-0 right-0 top-0 z-50 flex w-full max-w-2xl flex-col border-l border-gray-800 bg-gray-900 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <SeverityBadge severity={event.severity} />
            <span className="font-mono text-sm text-indigo-300">{event.service}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={copy}
              className="flex items-center gap-1.5 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs hover:bg-gray-700 transition-colors"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Copied!" : "Copy"}
            </button>
            {onDelete && (
              confirmDelete ? (
                <div className="flex items-center gap-1">
                  <button
                    onClick={async () => {
                      setDeleting(true);
                      onDelete(event.id);
                      setConfirmDelete(false);
                    }}
                    disabled={deleting}
                    className="flex items-center gap-1 rounded-md border border-red-700 bg-red-950 px-3 py-1.5 text-xs text-red-300 hover:bg-red-900 transition-colors disabled:opacity-50"
                  >
                    {deleting ? "Deleting…" : "Confirm"}
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="rounded-md border border-gray-700 bg-gray-800 px-2 py-1.5 text-xs hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="flex items-center gap-1.5 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs hover:bg-gray-700 hover:text-red-400 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete
                </button>
              )
            )}
            <button
              onClick={onClose}
              className="rounded-md p-1.5 hover:bg-gray-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Message */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Message</h3>
            <p className="text-gray-100 leading-relaxed">{event.message}</p>
          </div>

          {/* Meta */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">Timestamp</h3>
              <p className="text-sm font-mono text-gray-300">
                {format(new Date(event.timestamp), "yyyy-MM-dd HH:mm:ss 'UTC'")}
              </p>
            </div>
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">Environment</h3>
              <span className="inline-flex rounded px-2 py-0.5 text-xs bg-gray-800 text-gray-300">
                {event.environment || "production"}
              </span>
            </div>
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">Event ID</h3>
              <p className="text-xs font-mono text-gray-400 break-all">{event.id}</p>
            </div>
          </div>

          {/* Stack Trace */}
          {event.stack_trace ? (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Stack Trace</h3>
              <pre className="overflow-x-auto rounded-lg border border-gray-800 bg-gray-950 p-4 text-xs leading-relaxed text-gray-300 font-mono whitespace-pre-wrap break-words">
                {event.stack_trace}
              </pre>
            </div>
          ) : (
            <div className="rounded-lg border border-gray-800 bg-gray-950 p-4 text-center text-sm text-gray-500">
              No stack trace available
            </div>
          )}

          {/* Metadata */}
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">Metadata</h3>
              <pre className="overflow-x-auto rounded-lg border border-gray-800 bg-gray-950 p-4 text-xs leading-relaxed text-gray-300 font-mono">
                {JSON.stringify(event.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
