import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock client module
const mockApiPost = vi.fn();
const mockApiGet = vi.fn();

vi.mock("../client", () => ({
  apiPost: (...args: unknown[]) => mockApiPost(...args),
  apiGet: (...args: unknown[]) => mockApiGet(...args),
}));

import { refreshCardPrice, fetchPriceRequestStatus } from "../cards";

describe("cards API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPost.mockResolvedValue({ data: null });
    mockApiGet.mockResolvedValue({ data: null });
  });

  describe("refreshCardPrice", () => {
    it("passes timeoutMs: 30_000 to apiPost", async () => {
      await refreshCardPrice(42);

      expect(mockApiPost).toHaveBeenCalledWith(
        "/api/v1/cards/42/refresh-price",
        {},
        { timeoutMs: 30_000 },
      );
    });

    it("calls the correct endpoint with card ID", async () => {
      await refreshCardPrice(99);

      expect(mockApiPost).toHaveBeenCalledWith(
        "/api/v1/cards/99/refresh-price",
        {},
        expect.objectContaining({ timeoutMs: 30_000 }),
      );
    });
  });

  describe("fetchPriceRequestStatus", () => {
    it("calls the correct endpoint", async () => {
      await fetchPriceRequestStatus(42);

      expect(mockApiGet).toHaveBeenCalledWith(
        "/api/v1/cards/42/price-request-status",
      );
    });
  });
});
