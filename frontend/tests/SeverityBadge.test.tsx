import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import SeverityBadge from "@/components/SeverityBadge";

describe("SeverityBadge", () => {
  it("renders info badge", () => {
    render(<SeverityBadge severity="info" />);
    expect(screen.getByText("Info")).toBeInTheDocument();
  });

  it("renders warning badge", () => {
    render(<SeverityBadge severity="warning" />);
    expect(screen.getByText("Warning")).toBeInTheDocument();
  });

  it("renders error badge", () => {
    render(<SeverityBadge severity="error" />);
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("renders critical badge", () => {
    render(<SeverityBadge severity="critical" />);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("applies correct color classes for critical", () => {
    const { container } = render(<SeverityBadge severity="critical" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("red");
  });

  it("applies correct color classes for error", () => {
    const { container } = render(<SeverityBadge severity="error" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("orange");
  });
});
