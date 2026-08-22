import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BanEventCard } from "../../src/components/BanEventCard";

function renderCard(
  overrides: Partial<Parameters<typeof BanEventCard>[0]["event"]> = {},
  showCardInfo = true,
) {
  const event = {
    cardId: 1,
    nameEn: "Lightning Bolt",
    namePt: "Raio",
    setCode: "lea",
    collectorNumber: "161",
    format: "standard",
    oldStatus: "legal" as string | null,
    newStatus: "banned",
    changedAt: "2026-08-01T00:00:00",
    imageUrl: "https://example.com/img.jpg",
    ...overrides,
  };

  return render(
    <MemoryRouter>
      <BanEventCard event={event} showCardInfo={showCardInfo} />
    </MemoryRouter>,
  );
}

describe("BanEventCard", () => {
  it("renders card info when showCardInfo=true", () => {
    renderCard({}, true);
    expect(screen.getByTestId("ban-event-card")).toBeInTheDocument();
    expect(screen.getByTestId("ban-event-name")).toHaveTextContent(
      "Lightning Bolt",
    );
    expect(screen.getByTestId("ban-event-image")).toBeInTheDocument();
    expect(screen.getByTestId("ban-event-date")).toBeInTheDocument();
  });

  it("hides card info when showCardInfo=false", () => {
    renderCard({}, false);
    expect(screen.getByTestId("ban-event-card")).toBeInTheDocument();
    expect(screen.queryByTestId("ban-event-name")).toBeNull();
    expect(screen.queryByTestId("ban-event-image")).toBeNull();
  });

  it("renders format badge and transition", () => {
    renderCard({ format: "modern", oldStatus: "legal", newStatus: "banned" });
    expect(screen.getByTestId("status-transition")).toBeInTheDocument();
    // Format badge on the LegalityBadge
    expect(screen.getByText("Modern")).toBeInTheDocument();
  });

  it("renders date formatted", () => {
    renderCard({ changedAt: "2026-08-01T00:00:00" });
    expect(screen.getByTestId("ban-event-date")).toBeInTheDocument();
  });

  it("handles null oldStatus (initial entry)", () => {
    renderCard({ oldStatus: null, newStatus: "legal" });
    expect(screen.getByTestId("initial-label")).toBeInTheDocument();
  });
});
