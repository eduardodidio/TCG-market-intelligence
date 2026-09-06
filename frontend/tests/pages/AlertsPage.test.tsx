import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AlertsPage } from "../../src/pages/AlertsPage";

// Mock auth
vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: 1, email: "test@example.com" },
  }),
}));

// Mock alerts API
vi.mock("../../src/api/alerts", () => ({
  fetchAlerts: vi.fn(),
  deleteAlert: vi.fn(),
  fetchNotifications: vi.fn(),
  markAllNotificationsRead: vi.fn(),
}));

import { fetchAlerts, fetchNotifications } from "../../src/api/alerts";

const mockFetchAlerts = vi.mocked(fetchAlerts);
const mockFetchNotifications = vi.mocked(fetchNotifications);

function renderPage() {
  return render(
    <MemoryRouter>
      <AlertsPage />
    </MemoryRouter>,
  );
}

describe("AlertsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetchAlerts.mockResolvedValue({
      data: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "" },
      errors: [],
    });

    mockFetchNotifications.mockResolvedValue({
      data: { notifications: [], unread_count: 0 },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });
  });

  it("renders page title", async () => {
    renderPage();
    await waitFor(() => {
      // Title appears in both breadcrumb and heading
      const elements = screen.getAllByText("Price Alerts");
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders tab buttons", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("tab-active")).toBeDefined();
      expect(screen.getByTestId("tab-triggered")).toBeDefined();
    });
  });

  it("shows empty state for active alerts", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("No active alerts")).toBeDefined();
    });
  });

  it("shows active alerts when present", async () => {
    mockFetchAlerts.mockResolvedValueOnce({
      data: [
        {
          id: 1,
          card_id: 42,
          card_name: "Lightning Bolt",
          target_price: 10.0,
          direction: "below" as const,
          is_active: true,
          triggered_at: null,
          created_at: new Date().toISOString(),
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Lightning Bolt")).toBeDefined();
    });

    expect(screen.getByTestId("active-alerts-list")).toBeDefined();
  });

  it("switches to triggered tab", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("tab-triggered")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("tab-triggered"));

    await waitFor(() => {
      expect(screen.getByText("No triggered alerts")).toBeDefined();
    });
  });
});
