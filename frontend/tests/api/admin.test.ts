import { describe, it, expect, vi, beforeEach } from "vitest";

const mockApiGet = vi.fn();
const mockApiPatch = vi.fn();

vi.mock("../../src/api/client", () => ({
  apiGet: (...args: unknown[]) => mockApiGet(...args),
  apiPatch: (...args: unknown[]) => mockApiPatch(...args),
}));

vi.mock("../../src/utils/constants", () => ({
  API_BASE_URL: "http://localhost:8000",
  DEFAULT_PAGE_LIMIT: 24,
  GRID_SIZE_CONFIG: {},
}));

describe("fetchAdminUsers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockResolvedValue({
      data: [],
      errors: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "" },
    });
  });

  it("calls apiGet with default limit and offset", async () => {
    const { fetchAdminUsers } = await import("../../src/api/admin");
    await fetchAdminUsers();
    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/admin/users", {
      limit: "50",
      offset: "0",
    });
  });

  it("passes custom limit and offset", async () => {
    const { fetchAdminUsers } = await import("../../src/api/admin");
    await fetchAdminUsers(10, 20);
    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/admin/users", {
      limit: "10",
      offset: "20",
    });
  });
});

describe("adjustUserCredits", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPatch.mockResolvedValue({
      data: { user_id: 1, new_balance: 55, amount_applied: 5 },
      errors: [],
      meta: { cursor: null, total: null, offset: null, request_id: "" },
    });
  });

  it("calls apiPatch with user id, amount, and reason", async () => {
    const { adjustUserCredits } = await import("../../src/api/admin");
    await adjustUserCredits(1, 5, "bonus");
    expect(mockApiPatch).toHaveBeenCalledWith(
      "/api/v1/admin/users/1/credits",
      { amount: 5, reason: "bonus" },
    );
  });

  it("sends undefined reason when not provided", async () => {
    const { adjustUserCredits } = await import("../../src/api/admin");
    await adjustUserCredits(2, -10);
    expect(mockApiPatch).toHaveBeenCalledWith(
      "/api/v1/admin/users/2/credits",
      { amount: -10, reason: undefined },
    );
  });
});

describe("fetchAdminDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockResolvedValue({
      data: { total_users: 5 },
      errors: [],
      meta: { cursor: null, total: null, offset: null, request_id: "" },
    });
  });

  it("calls apiGet for dashboard endpoint", async () => {
    const { fetchAdminDashboard } = await import("../../src/api/admin");
    await fetchAdminDashboard();
    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/admin/dashboard");
  });
});
