import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminPanel } from "../../src/pages/AdminPanel";
import type { ApiResponse } from "../../src/types/api";
import type { AdminUser, AdminDashboard } from "../../src/api/admin";

function envelope<T>(data: T, total?: number): ApiResponse<T> {
  return {
    data,
    meta: {
      cursor: null,
      total: total ?? null,
      offset: null,
      request_id: "test",
    },
    errors: [],
  };
}

function errorEnvelope(message: string): ApiResponse<null> {
  return {
    data: null,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [{ code: "ERROR", message }],
  };
}

function mockUsers(): AdminUser[] {
  return [
    {
      id: 1,
      email: "admin@test.com",
      display_name: "Admin User",
      is_admin: true,
      is_active: true,
      credit_balance: 50,
      created_at: "2026-08-01T00:00:00",
    },
    {
      id: 2,
      email: "regular@test.com",
      display_name: null,
      is_admin: false,
      is_active: true,
      credit_balance: 0,
      created_at: "2026-08-02T00:00:00",
    },
  ];
}

function mockDashboardData(): AdminDashboard {
  return {
    total_users: 10,
    active_users: 8,
    admin_users: 2,
    total_credits_in_circulation: 500,
    total_credits_granted: 800,
    total_credits_spent: 300,
    total_collection_entries: 349,
    total_scans: 42,
  };
}

function createMockFetch(overrides?: {
  usersResponse?: ApiResponse<unknown>;
  dashboardResponse?: ApiResponse<unknown>;
  adjustResponse?: ApiResponse<unknown>;
}) {
  return vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    if (typeof url === "string" && url.includes("/admin/users") && init?.method === "PATCH") {
      const resp = overrides?.adjustResponse ?? envelope({
        user_id: 1,
        new_balance: 55,
        amount_applied: 5,
      });
      return Promise.resolve({
        ok: resp.errors.length === 0,
        status: resp.errors.length > 0 ? 400 : 200,
        statusText: "OK",
        json: () => Promise.resolve(resp),
      });
    }
    if (typeof url === "string" && url.includes("/admin/users")) {
      const resp = overrides?.usersResponse ?? envelope(mockUsers(), 2);
      return Promise.resolve({
        ok: resp.errors.length === 0,
        status: resp.errors.length > 0 ? 500 : 200,
        statusText: "OK",
        json: () => Promise.resolve(resp),
      });
    }
    if (typeof url === "string" && url.includes("/admin/dashboard")) {
      const resp = overrides?.dashboardResponse ?? envelope(mockDashboardData());
      return Promise.resolve({
        ok: resp.errors.length === 0,
        status: resp.errors.length > 0 ? 500 : 200,
        statusText: "OK",
        json: () => Promise.resolve(resp),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(envelope(null)),
    });
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminPanel />
    </MemoryRouter>,
  );
}

describe("AdminPanel", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders page container with correct testid", () => {
    renderPage();
    expect(screen.getByTestId("page-admin-panel")).toBeInTheDocument();
  });

  it("renders user table with mock data", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
      expect(screen.getByText("Admin User")).toBeInTheDocument();
      // User 2 has no display_name, so email appears in both Name and Email columns
      expect(screen.getByTestId("user-row-2")).toBeInTheDocument();
    });
  });

  it("shows balance=0 for users without credits", async () => {
    renderPage();
    await waitFor(() => {
      const balance = screen.getByTestId("balance-2");
      expect(balance.textContent).toBe("0");
    });
  });

  it("shows admin badge for admin users", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("admin-badge-1")).toBeInTheDocument();
    });
  });

  it("shows adjust credits button per user", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("adjust-btn-1")).toBeInTheDocument();
      expect(screen.getByTestId("adjust-btn-2")).toBeInTheDocument();
    });
  });

  it("opens adjust form when clicking adjust button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("adjust-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("adjust-btn-1"));

    expect(screen.getByTestId("adjust-form-1")).toBeInTheDocument();
    expect(screen.getByTestId("amount-input-1")).toBeInTheDocument();
    expect(screen.getByTestId("reason-input-1")).toBeInTheDocument();
    expect(screen.getByTestId("apply-btn-1")).toBeInTheDocument();
  });

  it("calls adjustUserCredits with correct params on apply", async () => {
    const fetchSpy = createMockFetch();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("adjust-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("adjust-btn-1"));

    const amountInput = screen.getByTestId("amount-input-1");
    const reasonInput = screen.getByTestId("reason-input-1");

    fireEvent.change(amountInput, { target: { value: "5" } });
    fireEvent.change(reasonInput, { target: { value: "bonus" } });
    fireEvent.click(screen.getByTestId("apply-btn-1"));

    await waitFor(() => {
      const patchCalls = fetchSpy.mock.calls.filter(
        ([, init]: [string, RequestInit | undefined]) => init?.method === "PATCH",
      );
      expect(patchCalls.length).toBeGreaterThan(0);
      const [patchUrl, patchInit] = patchCalls[0] as [string, RequestInit];
      expect(patchUrl).toContain("/admin/users/1/credits");
      const body = JSON.parse(patchInit.body as string);
      expect(body.amount).toBe(5);
      expect(body.reason).toBe("bonus");
    });
  });

  it("renders loading state", () => {
    // Make fetch hang forever
    globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {})) as unknown as typeof fetch;
    renderPage();
    expect(screen.getByTestId("users-loading")).toBeInTheDocument();
  });

  it("renders error state", async () => {
    globalThis.fetch = createMockFetch({
      usersResponse: errorEnvelope("Server error"),
    }) as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-error")).toBeInTheDocument();
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("pagination buttons update offset", async () => {
    // Return 100 total so next page is available
    const manyUsers = mockUsers();
    globalThis.fetch = createMockFetch({
      usersResponse: envelope(manyUsers, 100),
    }) as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
    });

    const nextBtn = screen.getByTestId("users-next");
    const prevBtn = screen.getByTestId("users-prev");

    // Prev should be disabled on first page
    expect(prevBtn).toBeDisabled();
    expect(nextBtn).not.toBeDisabled();

    fireEvent.click(nextBtn);

    // After clicking next, prev should be enabled
    await waitFor(() => {
      expect(screen.getByTestId("users-prev")).not.toBeDisabled();
    });
  });

  it("switches to dashboard tab and renders KPI cards", async () => {
    renderPage();

    // Wait for users tab to load first
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
    });

    // Click dashboard tab
    fireEvent.click(screen.getByTestId("tab-dashboard"));

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-section")).toBeInTheDocument();
      expect(screen.getByText("10")).toBeInTheDocument(); // total_users
      expect(screen.getByText("8")).toBeInTheDocument(); // active_users
      expect(screen.getByText("500")).toBeInTheDocument(); // credits_in_circulation
      expect(screen.getByText("800")).toBeInTheDocument(); // credits_granted
      expect(screen.getByText("300")).toBeInTheDocument(); // credits_spent
      expect(screen.getByText("349")).toBeInTheDocument(); // collection_entries
      expect(screen.getByText("42")).toBeInTheDocument(); // total_scans
    });
  });

  it("shows dashboard error state", async () => {
    globalThis.fetch = createMockFetch({
      dashboardResponse: errorEnvelope("Dashboard failed"),
    }) as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-dashboard"));

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-error")).toBeInTheDocument();
      expect(screen.getByText("Dashboard failed")).toBeInTheDocument();
    });
  });

  it("shows dashboard loading state", async () => {
    // First load users normally, then make dashboard hang
    let callCount = 0;
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (typeof url === "string" && url.includes("/admin/dashboard")) {
        return new Promise(() => {}); // hang
      }
      callCount++;
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockUsers(), 2)),
      });
    }) as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-dashboard"));

    expect(screen.getByTestId("dashboard-loading")).toBeInTheDocument();
  });

  it("renders tabs with correct testids", () => {
    renderPage();
    expect(screen.getByTestId("tab-users")).toBeInTheDocument();
    expect(screen.getByTestId("tab-dashboard")).toBeInTheDocument();
  });
});
