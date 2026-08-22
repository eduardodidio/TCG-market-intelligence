import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { StatusTransition } from "../../src/components/StatusTransition";

function renderTransition(oldStatus: string | null, newStatus: string) {
  return render(
    <MemoryRouter>
      <StatusTransition oldStatus={oldStatus} newStatus={newStatus} />
    </MemoryRouter>,
  );
}

describe("StatusTransition", () => {
  it("renders old and new badges when oldStatus is present", () => {
    renderTransition("legal", "banned");
    const transition = screen.getByTestId("status-transition");
    expect(transition).toBeInTheDocument();
    expect(screen.getByTestId("legality-badge-legal")).toBeInTheDocument();
    expect(screen.getByTestId("legality-badge-banned")).toBeInTheDocument();
    expect(screen.getByTestId("transition-arrow")).toBeInTheDocument();
  });

  it("shows initial label when oldStatus is null", () => {
    renderTransition(null, "banned");
    expect(screen.getByTestId("initial-label")).toBeInTheDocument();
    expect(screen.getByTestId("legality-badge-banned")).toBeInTheDocument();
    expect(screen.queryByTestId("transition-arrow")).toBeNull();
  });

  it("arrow is red for banned newStatus", () => {
    renderTransition("legal", "banned");
    const arrow = screen.getByTestId("transition-arrow");
    expect(arrow.getAttribute("class")).toContain("text-red-400");
  });

  it("arrow is red for restricted newStatus", () => {
    renderTransition("legal", "restricted");
    const arrow = screen.getByTestId("transition-arrow");
    expect(arrow.getAttribute("class")).toContain("text-red-400");
  });

  it("arrow is green for legal newStatus", () => {
    renderTransition("banned", "legal");
    const arrow = screen.getByTestId("transition-arrow");
    expect(arrow.getAttribute("class")).toContain("text-green-400");
  });

  it("arrow is gray for other newStatus", () => {
    renderTransition("legal", "not_legal");
    const arrow = screen.getByTestId("transition-arrow");
    expect(arrow.getAttribute("class")).toContain("text-slate-400");
  });
});
