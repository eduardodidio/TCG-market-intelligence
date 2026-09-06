import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AlertBell } from "../../src/components/AlertBell";

// Mock the useAlertNotifications hook
const mockMarkAllRead = vi.fn();
const mockRefetch = vi.fn();

vi.mock("../../src/hooks/useAlertNotifications", () => ({
  useAlertNotifications: () => ({
    notifications: mockNotifications,
    unreadCount: mockUnreadCount,
    loading: false,
    markAllRead: mockMarkAllRead,
    refetch: mockRefetch,
  }),
}));

let mockNotifications: Array<{
  id: number;
  alert_id: number;
  card_name: string;
  old_price: number | null;
  new_price: number;
  is_read: boolean;
  notified_at: string;
}> = [];
let mockUnreadCount = 0;

function renderBell() {
  return render(
    <MemoryRouter>
      <AlertBell />
    </MemoryRouter>,
  );
}

describe("AlertBell", () => {
  beforeEach(() => {
    mockNotifications = [];
    mockUnreadCount = 0;
    vi.clearAllMocks();
  });

  it("renders the bell button", () => {
    renderBell();
    expect(screen.getByTestId("alert-bell-button")).toBeDefined();
  });

  it("does not show badge when no unread notifications", () => {
    renderBell();
    expect(screen.queryByTestId("alert-badge")).toBeNull();
  });

  it("shows badge with unread count", () => {
    mockUnreadCount = 3;
    renderBell();
    const badge = screen.getByTestId("alert-badge");
    expect(badge.textContent).toBe("3");
  });

  it("shows 99+ for large counts", () => {
    mockUnreadCount = 150;
    renderBell();
    const badge = screen.getByTestId("alert-badge");
    expect(badge.textContent).toBe("99+");
  });

  it("opens dropdown on click", () => {
    renderBell();
    expect(screen.queryByTestId("alert-dropdown")).toBeNull();
    fireEvent.click(screen.getByTestId("alert-bell-button"));
    expect(screen.getByTestId("alert-dropdown")).toBeDefined();
  });

  it("shows empty state when no notifications", () => {
    renderBell();
    fireEvent.click(screen.getByTestId("alert-bell-button"));
    expect(screen.getByText("No notifications yet")).toBeDefined();
  });

  it("shows notification items", () => {
    mockNotifications = [
      {
        id: 1,
        alert_id: 1,
        card_name: "Lightning Bolt",
        old_price: 15.0,
        new_price: 8.0,
        is_read: false,
        notified_at: new Date().toISOString(),
      },
    ];
    mockUnreadCount = 1;

    renderBell();
    fireEvent.click(screen.getByTestId("alert-bell-button"));
    expect(screen.getByText("Lightning Bolt")).toBeDefined();
    expect(screen.getByText("R$ 15.00 → R$ 8.00")).toBeDefined();
  });

  it("shows mark all read button when unread", () => {
    mockUnreadCount = 1;
    mockNotifications = [
      {
        id: 1,
        alert_id: 1,
        card_name: "Test Card",
        old_price: null,
        new_price: 5.0,
        is_read: false,
        notified_at: new Date().toISOString(),
      },
    ];

    renderBell();
    fireEvent.click(screen.getByTestId("alert-bell-button"));
    const markBtn = screen.getByTestId("mark-all-read");
    expect(markBtn).toBeDefined();

    fireEvent.click(markBtn);
    expect(mockMarkAllRead).toHaveBeenCalled();
  });

  it("has a view all alerts link", () => {
    renderBell();
    fireEvent.click(screen.getByTestId("alert-bell-button"));
    const link = screen.getByTestId("view-all-alerts");
    expect(link.getAttribute("href")).toBe("/alerts");
  });
});
