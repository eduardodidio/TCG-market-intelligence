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
  updateAlert: vi.fn(),
}));

// Mock cards API (for CardSearchAlertModal)
vi.mock("../../src/api/cards", () => ({
  fetchCards: vi.fn(),
}));

import { fetchAlerts, fetchNotifications, updateAlert } from "../../src/api/alerts";

const mockFetchAlerts = vi.mocked(fetchAlerts);
const mockFetchNotifications = vi.mocked(fetchNotifications);
const mockUpdateAlert = vi.mocked(updateAlert);

function renderPage() {
  return render(
    <MemoryRouter>
      <AlertsPage />
    </MemoryRouter>,
  );
}

const emptyMeta = { cursor: null, total: 0, offset: null, request_id: "" };

describe("AlertsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetchAlerts.mockResolvedValue({
      data: [],
      meta: emptyMeta,
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

  it("renders Create Alert button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("create-alert-button")).toBeDefined();
    });
  });

  it("opens CardSearchAlertModal on Create Alert click", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("create-alert-button")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("create-alert-button"));

    await waitFor(() => {
      expect(screen.getByTestId("card-search-alert-modal")).toBeDefined();
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
          current_price: 18.5,
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

  it("card name renders as a link", async () => {
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
          current_price: null,
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      const link = screen.getByTestId("alert-card-link");
      expect(link).toBeDefined();
      expect(link.tagName).toBe("A");
      expect(link.getAttribute("href")).toBe("/cards/42");
    });
  });

  it("shows current price when available", async () => {
    mockFetchAlerts.mockResolvedValueOnce({
      data: [
        {
          id: 1,
          card_id: 42,
          card_name: "Lightning Bolt",
          target_price: 15.0,
          direction: "below" as const,
          is_active: true,
          triggered_at: null,
          created_at: new Date().toISOString(),
          current_price: 18.5,
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("alert-current-price")).toBeDefined();
      expect(screen.getByTestId("alert-current-price").textContent).toContain("18.50");
    });
  });

  it("shows inline edit button on active alerts", async () => {
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
          current_price: null,
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("inline-edit-button")).toBeDefined();
    });
  });

  it("clicking pencil icon enters edit mode", async () => {
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
          current_price: null,
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("inline-edit-button")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("inline-edit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("inline-edit-input")).toBeDefined();
    });
  });

  it("submitting inline edit calls updateAlert", async () => {
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
          current_price: null,
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    mockUpdateAlert.mockResolvedValue({
      data: {
        id: 1,
        card_id: 42,
        card_name: "Lightning Bolt",
        target_price: 25.0,
        direction: "below" as const,
        is_active: true,
        triggered_at: null,
        created_at: new Date().toISOString(),
        current_price: null,
      },
      meta: emptyMeta,
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("inline-edit-button")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("inline-edit-button"));
    const input = screen.getByTestId("inline-edit-input");
    fireEvent.change(input, { target: { value: "25.00" } });
    fireEvent.click(screen.getByTestId("inline-edit-save"));

    await waitFor(() => {
      expect(mockUpdateAlert).toHaveBeenCalledWith(1, { target_price: 25 });
    });
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

  it("triggered tab card name renders as link", async () => {
    // First call returns empty active alerts
    mockFetchAlerts.mockResolvedValueOnce({
      data: [],
      meta: emptyMeta,
      errors: [],
    });
    // Second call returns triggered alerts
    mockFetchAlerts.mockResolvedValueOnce({
      data: [
        {
          id: 2,
          card_id: 99,
          card_name: "Black Lotus",
          target_price: 50.0,
          direction: "above" as const,
          is_active: false,
          triggered_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          current_price: null,
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("tab-triggered")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("tab-triggered"));

    await waitFor(() => {
      const link = screen.getByTestId("alert-card-link");
      expect(link.tagName).toBe("A");
      expect(link.getAttribute("href")).toBe("/cards/99");
    });
  });
});
