import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminPanel } from "../../src/pages/AdminPanel";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";
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
  createResponse?: ApiResponse<unknown>;
  deleteResponse?: ApiResponse<unknown>;
}) {
  return vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    if (typeof url === "string" && url.includes("/admin/users") && init?.method === "POST") {
      const resp = overrides?.createResponse ?? envelope({
        user_id: 3,
        email: "new@test.com",
        display_name: "New User",
        temporary_password: "abc123xyz456",
      });
      return Promise.resolve({
        ok: resp.errors.length === 0,
        status: resp.errors.length > 0 ? 409 : 200,
        statusText: "OK",
        json: () => Promise.resolve(resp),
      });
    }
    if (typeof url === "string" && url.includes("/admin/users") && init?.method === "DELETE") {
      const resp = overrides?.deleteResponse ?? envelope({ user_id: 2, deleted: true });
      return Promise.resolve({
        ok: resp.errors.length === 0,
        status: resp.errors.length > 0 ? 400 : 200,
        statusText: "OK",
        json: () => Promise.resolve(resp),
      });
    }
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

const mockAuthValue: AuthContextValue = {
  user: {
    id: 1,
    email: "admin@test.com",
    display_name: "Admin User",
    avatar_url: null,
    auth_provider: "email",
    preferred_language: "en",
    is_active: true,
    is_admin: true,
  },
  loading: false,
  error: null,
  isAuthenticated: true,
  mustChangePassword: false,
  login: vi.fn().mockResolvedValue(null),
  register: vi.fn().mockResolvedValue(null),
  logout: vi.fn(),
  changePassword: vi.fn().mockResolvedValue(null),
};

function renderPage() {
  return render(
    <AuthContext.Provider value={mockAuthValue}>
      <MemoryRouter>
        <AdminPanel />
      </MemoryRouter>
    </AuthContext.Provider>,
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

  it("renders 5 accordion sections", () => {
    renderPage();
    expect(screen.getByTestId("accordion-users")).toBeInTheDocument();
    expect(screen.getByTestId("accordion-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("accordion-liga-status")).toBeInTheDocument();
    expect(screen.getByTestId("accordion-schedules")).toBeInTheDocument();
    expect(screen.getByTestId("accordion-price-scans")).toBeInTheDocument();
  });

  it("default open section is users", async () => {
    renderPage();
    // Users section should be open and visible
    await waitFor(() => {
      expect(screen.getByTestId("users-section")).toBeInTheDocument();
    });
    // Dashboard section should not be visible
    expect(screen.queryByTestId("dashboard-section")).not.toBeInTheDocument();
  });

  it("only one section open at a time", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-section")).toBeInTheDocument();
    });

    // Click dashboard accordion
    fireEvent.click(screen.getByTestId("accordion-toggle-dashboard"));

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-section")).toBeInTheDocument();
    });
    // Users section should now be hidden
    expect(screen.queryByTestId("users-section")).not.toBeInTheDocument();
  });

  it("clicking open section closes it", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-section")).toBeInTheDocument();
    });

    // Click users toggle to close it
    fireEvent.click(screen.getByTestId("accordion-toggle-users"));

    // All sections should be closed
    expect(screen.queryByTestId("users-section")).not.toBeInTheDocument();
    expect(screen.queryByTestId("dashboard-section")).not.toBeInTheDocument();
  });

  it("renders user table with mock data", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
      expect(screen.getByText("Admin User")).toBeInTheDocument();
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

  it("opens adjust form when clicking adjust button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("adjust-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("adjust-btn-1"));
    expect(screen.getByTestId("adjust-form-1")).toBeInTheDocument();
  });

  it("calls adjustUserCredits with correct params on apply", async () => {
    const fetchSpy = createMockFetch();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("adjust-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("adjust-btn-1"));
    fireEvent.change(screen.getByTestId("amount-input-1"), { target: { value: "5" } });
    fireEvent.change(screen.getByTestId("reason-input-1"), { target: { value: "bonus" } });
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

  it("renders error state for users", async () => {
    globalThis.fetch = createMockFetch({
      usersResponse: errorEnvelope("Server error"),
    }) as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-error")).toBeInTheDocument();
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("switches to dashboard section and renders KPI cards", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("accordion-toggle-dashboard"));

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-section")).toBeInTheDocument();
      expect(screen.getByText("10")).toBeInTheDocument(); // total_users
      expect(screen.getByText("8")).toBeInTheDocument(); // active_users
      expect(screen.getByText("500")).toBeInTheDocument(); // credits_in_circulation
    });
  });

  it("shows dashboard error state", async () => {
    globalThis.fetch = createMockFetch({
      dashboardResponse: errorEnvelope("Dashboard failed"),
    }) as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-section")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("accordion-toggle-dashboard"));

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-error")).toBeInTheDocument();
      expect(screen.getByText("Dashboard failed")).toBeInTheDocument();
    });
  });

  it("renders create user toggle button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("create-user-toggle")).toBeInTheDocument();
    });
  });

  it("shows temp password after creating user", async () => {
    const fetchSpy = createMockFetch();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("create-user-toggle")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("create-user-toggle"));
    fireEvent.change(screen.getByTestId("create-email-input"), {
      target: { value: "new@test.com" },
    });
    fireEvent.click(screen.getByTestId("create-user-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("temp-password")).toBeInTheDocument();
      expect(screen.getByTestId("temp-password").textContent).toBe("abc123xyz456");
    });
  });

  it("shows delete button for other users but not self", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("delete-btn-1")).not.toBeInTheDocument();
    expect(screen.getByTestId("delete-btn-2")).toBeInTheDocument();
  });

  it("pagination buttons update offset", async () => {
    globalThis.fetch = createMockFetch({
      usersResponse: envelope(mockUsers(), 100),
    }) as unknown as typeof fetch;

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("users-table")).toBeInTheDocument();
    });

    const nextBtn = screen.getByTestId("users-next");
    const prevBtn = screen.getByTestId("users-prev");
    expect(prevBtn).toBeDisabled();
    expect(nextBtn).not.toBeDisabled();

    fireEvent.click(nextBtn);
    await waitFor(() => {
      expect(screen.getByTestId("users-prev")).not.toBeDisabled();
    });
  });
});
