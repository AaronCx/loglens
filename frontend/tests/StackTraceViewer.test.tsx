import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import StackTraceViewer from "@/components/StackTraceViewer";
import type { Event } from "@/lib/types";

const mockEvent: Event = {
  id: "abc-123",
  timestamp: "2026-03-07T12:00:00Z",
  severity: "error",
  service: "auth-service",
  message: "Authentication failed for user",
  stack_trace: 'Traceback (most recent call last):\n  File "app.py", line 42\nValueError: invalid token',
  metadata: { user_id: "u-42", endpoint: "/login" },
  environment: "production",
};

const mockEventNoTrace: Event = {
  ...mockEvent,
  id: "def-456",
  stack_trace: null,
  metadata: null,
};

describe("StackTraceViewer", () => {
  it("renders event details", () => {
    render(<StackTraceViewer event={mockEvent} onClose={() => {}} />);
    expect(screen.getByText("Authentication failed for user")).toBeInTheDocument();
    expect(screen.getByText("auth-service")).toBeInTheDocument();
    expect(screen.getByText("production")).toBeInTheDocument();
  });

  it("renders stack trace when available", () => {
    render(<StackTraceViewer event={mockEvent} onClose={() => {}} />);
    expect(screen.getByText(/Traceback/)).toBeInTheDocument();
    expect(screen.getByText(/ValueError: invalid token/)).toBeInTheDocument();
  });

  it("shows no stack trace message when absent", () => {
    render(<StackTraceViewer event={mockEventNoTrace} onClose={() => {}} />);
    expect(screen.getByText("No stack trace available")).toBeInTheDocument();
  });

  it("renders metadata as JSON", () => {
    render(<StackTraceViewer event={mockEvent} onClose={() => {}} />);
    expect(screen.getByText(/u-42/)).toBeInTheDocument();
    expect(screen.getByText(/\/login/)).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<StackTraceViewer event={mockEvent} onClose={onClose} />);
    // Click the backdrop
    const backdrop = document.querySelector(".fixed.inset-0");
    if (backdrop) fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it("displays event ID", () => {
    render(<StackTraceViewer event={mockEvent} onClose={() => {}} />);
    expect(screen.getByText("abc-123")).toBeInTheDocument();
  });
});
