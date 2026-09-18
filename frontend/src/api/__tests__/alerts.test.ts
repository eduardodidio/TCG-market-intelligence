import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock client module
const mockApiPatch = vi.fn();
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiDelete = vi.fn();

vi.mock("../client", () => ({
  apiPatch: (...args: unknown[]) => mockApiPatch(...args),
  apiGet: (...args: unknown[]) => mockApiGet(...args),
  apiPost: (...args: unknown[]) => mockApiPost(...args),
  apiDelete: (...args: unknown[]) => mockApiDelete(...args),
}));

import { updateAlert } from "../alerts";

describe("alerts API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPatch.mockResolvedValue({ data: null });
  });

  describe("updateAlert", () => {
    it("calls apiPatch with correct endpoint and body", async () => {
      await updateAlert(42, { target_price: 25.0 });

      expect(mockApiPatch).toHaveBeenCalledWith(
        "/api/v1/alerts/42",
        { target_price: 25.0 },
      );
    });

    it("passes direction only", async () => {
      await updateAlert(7, { direction: "above" });

      expect(mockApiPatch).toHaveBeenCalledWith(
        "/api/v1/alerts/7",
        { direction: "above" },
      );
    });

    it("passes both fields", async () => {
      await updateAlert(1, { target_price: 10, direction: "below" });

      expect(mockApiPatch).toHaveBeenCalledWith(
        "/api/v1/alerts/1",
        { target_price: 10, direction: "below" },
      );
    });
  });
});
