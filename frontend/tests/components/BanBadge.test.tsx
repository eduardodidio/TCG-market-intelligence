import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BanBadge } from "../../src/components/BanBadge";

describe("BanBadge", () => {
  it("renders BANNED with red styling", () => {
    render(<BanBadge status="banned" />);
    const badge = screen.getByTestId("ban-badge-banned");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-red-600");
    expect(badge.textContent).toBe("BANNED");
  });

  it("renders RESTRICTED with yellow styling", () => {
    render(<BanBadge status="restricted" />);
    const badge = screen.getByTestId("ban-badge-restricted");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-yellow-600");
    expect(badge.textContent).toBe("RESTRICTED");
  });

  it("has pulsing ring when recentlyChanged", () => {
    render(<BanBadge status="banned" recentlyChanged />);
    const badge = screen.getByTestId("ban-badge-banned");
    expect(badge.className).toContain("animate-pulse");
    expect(badge.className).toContain("ring-2");
  });

  it("no pulsing ring when not recentlyChanged", () => {
    render(<BanBadge status="banned" recentlyChanged={false} />);
    const badge = screen.getByTestId("ban-badge-banned");
    expect(badge.className).not.toContain("animate-pulse");
  });
});
