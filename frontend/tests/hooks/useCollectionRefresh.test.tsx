import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCollectionRefresh } from "../../src/hooks/useCollectionRefresh";

// Track the last request passed to triggerScanAuth
let lastTriggerRequest: Record<string, unknown> | null = null;

vi.mock("../../src/api/scans", () => ({
  triggerScanAuth: vi.fn((request: Record<string, unknown>) => {
    lastTriggerRequest = request;
    return Promise.resolve({
      data: { scan_id: 1, status: "running" },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });
  }),
}));

vi.mock("../../src/hooks/useScanStream", () => ({
  useScanStream: () => ({
    disconnect: vi.fn(),
  }),
}));

beforeEach(() => {
  lastTriggerRequest = null;
  localStorage.clear();
});

describe("useCollectionRefresh", () => {
  it("passes maxAgeDays to triggerScanAuth when provided", async () => {
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh(3);
    });

    expect(lastTriggerRequest).toBeTruthy();
    expect(lastTriggerRequest!.max_age_days).toBe(3);
    expect(lastTriggerRequest!.scan_type).toBe("collection");
    expect(lastTriggerRequest!.provider).toBe("liga");
  });

  it("does not include max_age_days when not provided", async () => {
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh();
    });

    expect(lastTriggerRequest).toBeTruthy();
    expect(lastTriggerRequest!).not.toHaveProperty("max_age_days");
  });

  it("passes maxAgeDays=1 correctly", async () => {
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh(1);
    });

    expect(lastTriggerRequest!.max_age_days).toBe(1);
  });

  it("passes maxAgeDays=7 correctly", async () => {
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh(7);
    });

    expect(lastTriggerRequest!.max_age_days).toBe(7);
  });
});
