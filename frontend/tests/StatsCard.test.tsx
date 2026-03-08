import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StatsCard from "@/components/StatsCard";

describe("StatsCard", () => {
  it("renders label and value", () => {
    render(
      <StatsCard label="Total Events" value={1234} icon={<span>icon</span>} color="indigo" />
    );
    expect(screen.getByText("Total Events")).toBeInTheDocument();
    expect(screen.getByText("1,234")).toBeInTheDocument();
  });

  it("renders zero value", () => {
    render(
      <StatsCard label="Critical" value={0} icon={<span>icon</span>} color="red" />
    );
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("formats large numbers with locale", () => {
    render(
      <StatsCard label="Events" value={1000000} icon={<span>icon</span>} color="indigo" />
    );
    expect(screen.getByText("1,000,000")).toBeInTheDocument();
  });

  it("renders the icon", () => {
    render(
      <StatsCard label="Test" value={5} icon={<span data-testid="test-icon">I</span>} color="green" />
    );
    expect(screen.getByTestId("test-icon")).toBeInTheDocument();
  });
});
