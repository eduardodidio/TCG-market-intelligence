import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminPriceRequestsSection } from "../admin/AdminPriceRequestsSection";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "common.loading": "Loading...",
        "common.of": "of",
        "common.prev": "Previous",
        "common.next": "Next",
        "admin.priceRequests.pending": "Pending",
        "admin.priceRequests.processing": "Processing",
        "admin.priceRequests.completed": "Completed",
        "admin.priceRequests.failed": "Failed",
        "admin.priceRequests.allFilter": "All",
        "admin.priceRequests.noRequests": "No price requests",
        "admin.priceRequests.colCardName": "Card Name",
        "admin.priceRequests.colUserId": "User ID",
        "admin.priceRequests.colStatus": "Status",
        "admin.priceRequests.colRequested": "Requested",
        "admin.priceRequests.colProcessed": "Processed",
        "admin.priceRequests.colPrice": "Price",
        "admin.priceRequests.colError": "Error",
        "admin.priceRequests.colAttempts": "Attempts",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

const mockFetchPriceRequests = vi.fn();
const mockFetchPriceRequestStats = vi.fn();

vi.mock("../../api/admin", () => ({
  fetchAdminPriceRequests: (...args: unknown[]) =>
    mockFetchPriceRequests(...args),
  fetchAdminPriceRequestStats: (...args: unknown[]) =>
    mockFetchPriceRequestStats(...args),
}));

const emptyMeta = { cursor: null, total: null, offset: null, request_id: "" };

const sampleStats = {
  pending: 5,
  processing: 1,
  completed: 120,
  failed: 3,
};

const sampleRequests = [
  {
    id: 1,
    card_id: 10,
    card_name: "Lightning Bolt",
    user_id: 1,
    status: "pending",
    requested_at: "2026-09-17T12:00:00",
    processed_at: null,
    result_price: null,
    error_message: null,
    attempts: 0,
  },
  {
    id: 2,
    card_id: 20,
    card_name: "Counterspell",
    user_id: 2,
    status: "completed",
    requested_at: "2026-09-17T11:00:00",
    processed_at: "2026-09-17T11:05:00",
    result_price: 2.5,
    error_message: null,
    attempts: 1,
  },
  {
    id: 3,
    card_id: 30,
    card_name: "Dark Ritual",
    user_id: 1,
    status: "failed",
    requested_at: "2026-09-17T10:00:00",
    processed_at: "2026-09-17T10:02:00",
    result_price: null,
    error_message: "Card not found on Liga",
    attempts: 3,
  },
];

function setupSuccessMocks(items = sampleRequests, total?: number) {
  mockFetchPriceRequestStats.mockResolvedValue({
    data: sampleStats,
    meta: emptyMeta,
    errors: [],
  });
  mockFetchPriceRequests.mockResolvedValue({
    data: { items, total: total ?? items.length },
    meta: emptyMeta,
    errors: [],
  });
}

describe("AdminPriceRequestsSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render content until isOpen is true", () => {
    mockFetchPriceRequestStats.mockResolvedValue({
      data: null,
      meta: emptyMeta,
      errors: [],
    });
    mockFetchPriceRequests.mockResolvedValue({
      data: null,
      meta: emptyMeta,
      errors: [],
    });

    const { rerender } = render(
      <AdminPriceRequestsSection isOpen={false} />,
    );
    expect(screen.queryByTestId("price-requests-section")).not.toBeInTheDocument();

    // Open it
    rerender(<AdminPriceRequestsSection isOpen={true} />);
    expect(screen.getByTestId("price-requests-section")).toBeInTheDocument();
  });

  it("renders stats badges with correct counts", async () => {
    setupSuccessMocks();

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-stats")).toBeInTheDocument();
    });

    const pendingBadge = screen.getByTestId("stats-badge-Pending");
    expect(pendingBadge).toHaveTextContent("5");

    const processingBadge = screen.getByTestId("stats-badge-Processing");
    expect(processingBadge).toHaveTextContent("1");

    const completedBadge = screen.getByTestId("stats-badge-Completed");
    expect(completedBadge).toHaveTextContent("120");

    const failedBadge = screen.getByTestId("stats-badge-Failed");
    expect(failedBadge).toHaveTextContent("3");
  });

  it("renders filter tabs", async () => {
    setupSuccessMocks();

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(
        screen.getByTestId("price-requests-filter-tabs"),
      ).toBeInTheDocument();
    });

    expect(screen.getByTestId("filter-tab-all")).toBeInTheDocument();
    expect(screen.getByTestId("filter-tab-pending")).toBeInTheDocument();
    expect(screen.getByTestId("filter-tab-processing")).toBeInTheDocument();
    expect(screen.getByTestId("filter-tab-completed")).toBeInTheDocument();
    expect(screen.getByTestId("filter-tab-failed")).toBeInTheDocument();
  });

  it("table displays request data correctly", async () => {
    setupSuccessMocks();

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-table")).toBeInTheDocument();
    });

    // Row 1: Lightning Bolt - pending
    const row1 = screen.getByTestId("price-request-row-1");
    expect(row1).toHaveTextContent("Lightning Bolt");
    expect(row1).toHaveTextContent("pending");

    // Row 2: Counterspell - completed with price
    const row2 = screen.getByTestId("price-request-row-2");
    expect(row2).toHaveTextContent("Counterspell");
    expect(row2).toHaveTextContent("R$ 2.50");
    expect(row2).toHaveTextContent("completed");

    // Row 3: Dark Ritual - failed with error
    const row3 = screen.getByTestId("price-request-row-3");
    expect(row3).toHaveTextContent("Dark Ritual");
    expect(row3).toHaveTextContent("failed");
    expect(row3).toHaveTextContent("Card not found on Liga");
    expect(row3).toHaveTextContent("3");
  });

  it("empty state shown when no requests", async () => {
    mockFetchPriceRequestStats.mockResolvedValue({
      data: { pending: 0, processing: 0, completed: 0, failed: 0 },
      meta: emptyMeta,
      errors: [],
    });
    mockFetchPriceRequests.mockResolvedValue({
      data: { items: [], total: 0 },
      meta: emptyMeta,
      errors: [],
    });

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-empty")).toBeInTheDocument();
    });

    expect(screen.getByTestId("price-requests-empty")).toHaveTextContent(
      "No price requests",
    );
  });

  it("status badges have correct color classes", async () => {
    setupSuccessMocks();

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-table")).toBeInTheDocument();
    });

    const pendingBadge = screen.getByTestId("status-badge-pending");
    expect(pendingBadge.className).toContain("bg-yellow-900");
    expect(pendingBadge.className).toContain("text-yellow-300");

    const completedBadge = screen.getByTestId("status-badge-completed");
    expect(completedBadge.className).toContain("bg-green-900");
    expect(completedBadge.className).toContain("text-green-300");

    const failedBadge = screen.getByTestId("status-badge-failed");
    expect(failedBadge.className).toContain("bg-red-900");
    expect(failedBadge.className).toContain("text-red-300");
  });

  it("filter tabs change the API request status parameter", async () => {
    setupSuccessMocks();

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-table")).toBeInTheDocument();
    });

    // Initial load: "all" filter, no status param
    expect(mockFetchPriceRequests).toHaveBeenCalledWith({
      status: undefined,
      limit: 50,
      offset: 0,
    });

    // Click "Pending" filter
    fireEvent.click(screen.getByTestId("filter-tab-pending"));

    await waitFor(() => {
      expect(mockFetchPriceRequests).toHaveBeenCalledWith({
        status: "pending",
        limit: 50,
        offset: 0,
      });
    });

    // Click "Failed" filter
    fireEvent.click(screen.getByTestId("filter-tab-failed"));

    await waitFor(() => {
      expect(mockFetchPriceRequests).toHaveBeenCalledWith({
        status: "failed",
        limit: 50,
        offset: 0,
      });
    });
  });

  it("pagination controls appear and work", async () => {
    // Return 60 total items (more than page size of 50)
    setupSuccessMocks(sampleRequests, 60);

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-table")).toBeInTheDocument();
    });

    // Pagination info shown
    expect(screen.getByTestId("price-requests-pagination-info")).toHaveTextContent(
      "1--50 of 60",
    );

    // Previous disabled, Next enabled
    expect(screen.getByTestId("price-requests-prev")).toBeDisabled();
    expect(screen.getByTestId("price-requests-next")).not.toBeDisabled();

    // Click next
    fireEvent.click(screen.getByTestId("price-requests-next"));

    await waitFor(() => {
      expect(mockFetchPriceRequests).toHaveBeenCalledWith({
        status: undefined,
        limit: 50,
        offset: 50,
      });
    });
  });

  it("shows loading state", async () => {
    // Make requests never resolve to see loading state
    mockFetchPriceRequestStats.mockResolvedValue({
      data: sampleStats,
      meta: emptyMeta,
      errors: [],
    });
    mockFetchPriceRequests.mockReturnValue(new Promise(() => {}));

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-loading")).toBeInTheDocument();
    });

    expect(screen.getByTestId("price-requests-loading")).toHaveTextContent(
      "Loading...",
    );
  });
});
