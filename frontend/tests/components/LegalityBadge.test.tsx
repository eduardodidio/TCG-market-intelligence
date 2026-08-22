import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LegalityBadge } from "../../src/components/LegalityBadge";

describe("LegalityBadge", () => {
  it("renders correct color for banned status", () => {
    render(<LegalityBadge status="banned" />);
    const badge = screen.getByTestId("legality-badge-banned");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("text-red-400");
  });

  it("renders correct color for legal status", () => {
    render(<LegalityBadge status="legal" />);
    const badge = screen.getByTestId("legality-badge-legal");
    expect(badge.className).toContain("text-green-400");
  });

  it("renders correct color for restricted status", () => {
    render(<LegalityBadge status="restricted" />);
    const badge = screen.getByTestId("legality-badge-restricted");
    expect(badge.className).toContain("text-yellow-400");
  });

  it("renders correct color for not_legal status", () => {
    render(<LegalityBadge status="not_legal" />);
    const badge = screen.getByTestId("legality-badge-not_legal");
    expect(badge.className).toContain("text-slate-400");
  });

  it("renders format name when provided", () => {
    render(<LegalityBadge status="banned" format="standard" />);
    const formatEl = screen.getByTestId("legality-format");
    expect(formatEl.textContent).toBe("Standard");
  });

  it("does not render format when not provided", () => {
    render(<LegalityBadge status="legal" />);
    expect(screen.queryByTestId("legality-format")).toBeNull();
  });

  it("renders translated status text", () => {
    render(<LegalityBadge status="banned" />);
    const statusEl = screen.getByTestId("legality-status");
    expect(statusEl.textContent).toBe("Banned");
  });

  it("uses small size classes", () => {
    render(<LegalityBadge status="legal" size="sm" />);
    const badge = screen.getByTestId("legality-badge-legal");
    expect(badge.className).toContain("text-xs");
  });

  it("uses medium size classes by default", () => {
    render(<LegalityBadge status="legal" />);
    const badge = screen.getByTestId("legality-badge-legal");
    expect(badge.className).toContain("text-sm");
  });

  it("handles unknown status gracefully", () => {
    render(<LegalityBadge status="unknown_status" />);
    const badge = screen.getByTestId("legality-badge-unknown_status");
    expect(badge).toBeInTheDocument();
  });
});
