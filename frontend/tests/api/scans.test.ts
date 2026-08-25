import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock apiPost/apiGet
const mockApiPost = vi.fn();
const mockApiGet = vi.fn();

vi.mock("../../src/api/client", () => ({
  apiPost: (...args: unknown[]) => mockApiPost(...args),
  apiGet: (...args: unknown[]) => mockApiGet(...args),
}));

vi.mock("../../src/utils/constants", () => ({
  API_BASE_URL: "http://localhost:8000",
  DEFAULT_PAGE_LIMIT: 24,
  GRID_SIZE_CONFIG: {},
}));

describe("triggerScanAuth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPost.mockResolvedValue({
      data: { scan_id: 1, status: "pending" },
      errors: [],
      meta: { cursor: null, total: null, offset: null, request_id: "" },
    });
  });

  it("sends provider field defaulting to liga", async () => {
    const { triggerScanAuth } = await import("../../src/api/scans");

    await triggerScanAuth({ scan_type: "collection" });

    expect(mockApiPost).toHaveBeenCalledWith("/api/v1/scans", {
      scan_type: "collection",
      provider: "liga",
    });
  });

  it("sends explicit provider when specified", async () => {
    const { triggerScanAuth } = await import("../../src/api/scans");

    await triggerScanAuth({ scan_type: "collection", provider: "myp" });

    expect(mockApiPost).toHaveBeenCalledWith("/api/v1/scans", {
      scan_type: "collection",
      provider: "myp",
    });
  });

  it("preserves liga when explicitly passed", async () => {
    const { triggerScanAuth } = await import("../../src/api/scans");

    await triggerScanAuth({ scan_type: "collection", provider: "liga" });

    expect(mockApiPost).toHaveBeenCalledWith("/api/v1/scans", {
      scan_type: "collection",
      provider: "liga",
    });
  });
});
