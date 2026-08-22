import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { LegalityPanel } from "../../src/components/LegalityPanel";

// Mock the API
vi.mock("../../src/api/banEngine", () => ({
  fetchEntryLegalities: vi.fn(),
}));

import { fetchEntryLegalities } from "../../src/api/banEngine";

const mockLegalities = [
  { format: "standard", status: "banned", effective_date: null, recently_changed: true, change_date: "2026-08-20T00:00:00", old_status: "legal" },
  { format: "modern", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "vintage", status: "restricted", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "legacy", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "commander", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "pioneer", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "pauper", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "brawl", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "historic", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  { format: "alchemy", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
];

function mockApiResponse(data: unknown) {
  return Promise.resolve({
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "r1" },
    errors: [],
  });
}

describe("LegalityPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows unavailable message for null cardId", () => {
    render(<LegalityPanel entryId={1} cardId={null} />);
    expect(screen.getByTestId("legality-panel")).toBeInTheDocument();
    expect(screen.getByText(/not available/i)).toBeInTheDocument();
  });

  it("shows loading skeleton while fetching", () => {
    (fetchEntryLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise(() => {}), // never resolves
    );
    render(<LegalityPanel entryId={1} cardId={42} />);
    expect(screen.getByTestId("legality-skeleton")).toBeInTheDocument();
  });

  it("renders legality badges after loading", async () => {
    (fetchEntryLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(mockLegalities),
    );
    render(<LegalityPanel entryId={1} cardId={42} />);
    await waitFor(() => {
      expect(screen.getByTestId("legality-panel")).toBeInTheDocument();
    });
    // Should show badges (first 8 by default)
    expect(screen.getAllByTestId(/legality-badge/).length).toBeGreaterThan(0);
  });

  it("shows NEW chip for recently changed", async () => {
    (fetchEntryLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(mockLegalities),
    );
    render(<LegalityPanel entryId={1} cardId={42} />);
    await waitFor(() => {
      expect(screen.getByTestId("legality-new-standard")).toBeInTheDocument();
    });
  });

  it("shows expand button when more than 8 formats", async () => {
    (fetchEntryLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(mockLegalities),
    );
    render(<LegalityPanel entryId={1} cardId={42} />);
    await waitFor(() => {
      expect(screen.getByTestId("legality-panel-expand")).toBeInTheDocument();
    });
  });

  it("expand button toggles visibility", async () => {
    (fetchEntryLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(mockLegalities),
    );
    render(<LegalityPanel entryId={1} cardId={42} />);
    await waitFor(() => {
      expect(screen.getByTestId("legality-panel-expand")).toBeInTheDocument();
    });

    // Initially 8 badges shown
    const badgesBefore = screen.getAllByTestId(/legality-badge/);
    expect(badgesBefore.length).toBeLessThanOrEqual(8);

    // Click expand
    fireEvent.click(screen.getByTestId("legality-panel-expand"));
    const badgesAfter = screen.getAllByTestId(/legality-badge/);
    expect(badgesAfter.length).toBe(10);
  });

  it("shows empty message when no legality data", async () => {
    (fetchEntryLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse([]),
    );
    render(<LegalityPanel entryId={1} cardId={42} />);
    await waitFor(() => {
      expect(screen.getByText(/no legality data/i)).toBeInTheDocument();
    });
  });
});
