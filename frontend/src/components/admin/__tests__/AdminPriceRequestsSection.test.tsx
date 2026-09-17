import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AdminPriceRequestsSection } from "../AdminPriceRequestsSection";

// Mock admin API
const mockFetchStats = vi.fn();
const mockFetchRequests = vi.fn();
const mockTriggerProcess = vi.fn();

vi.mock("../../../api/admin", () => ({
  fetchAdminPriceRequestStats: (...args: unknown[]) => mockFetchStats(...args),
  fetchAdminPriceRequests: (...args: unknown[]) => mockFetchRequests(...args),
  triggerProcessPriceRequests: (...args: unknown[]) => mockTriggerProcess(...args),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts?.count !== undefined) return `${key} (${opts.count})`;
      return opts?.defaultValue ?? key;
    },
  }),
}));

describe("AdminPriceRequestsSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchStats.mockResolvedValue({
      data: { pending: 5, processing: 0, completed: 10, failed: 2 },
    });
    mockFetchRequests.mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            card_id: 42,
            card_name: "Lightning Bolt",
            user_id: 1,
            status: "pending",
            requested_at: "2026-09-17T10:00:00",
            processed_at: null,
            result_price: null,
            error_message: null,
            attempts: 0,
          },
        ],
        total: 1,
      },
    });
  });

  it("renders process queue button with pending count", async () => {
    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      const btn = screen.getByTestId("process-queue-btn");
      expect(btn).toBeInTheDocument();
      expect(btn).not.toBeDisabled();
    });
  });

  it("disables button when no pending requests", async () => {
    mockFetchStats.mockResolvedValue({
      data: { pending: 0, processing: 0, completed: 10, failed: 2 },
    });

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      const btn = screen.getByTestId("process-queue-btn");
      expect(btn).toBeDisabled();
    });
  });

  it("triggers API call when button is clicked", async () => {
    mockTriggerProcess.mockResolvedValue({
      data: { scan_id: 1, status: "started", pending_count: 5 },
    });

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("process-queue-btn")).not.toBeDisabled();
    });

    fireEvent.click(screen.getByTestId("process-queue-btn"));

    await waitFor(() => {
      expect(mockTriggerProcess).toHaveBeenCalled();
    });
  });

  it("shows processing feedback after trigger", async () => {
    mockTriggerProcess.mockResolvedValue({
      data: { scan_id: 1, status: "started", pending_count: 5 },
    });

    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("process-queue-btn")).not.toBeDisabled();
    });

    fireEvent.click(screen.getByTestId("process-queue-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("process-message")).toBeInTheDocument();
    });
  });

  it("renders stats badges", async () => {
    render(<AdminPriceRequestsSection isOpen={true} />);

    await waitFor(() => {
      expect(screen.getByTestId("price-requests-stats")).toBeInTheDocument();
    });
  });

  it("does not render when isOpen is false", () => {
    render(<AdminPriceRequestsSection isOpen={false} />);
    expect(screen.queryByTestId("price-requests-section")).not.toBeInTheDocument();
  });
});
