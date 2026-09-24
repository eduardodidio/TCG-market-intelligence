import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useCredits } from "../useCredits";
import { CREDITS_CHANGED_EVENT } from "../../utils/creditsEvents";

const mockFetchCreditBalance = vi.fn();
vi.mock("../../api/credits", () => ({
  fetchCreditBalance: (...args: unknown[]) => mockFetchCreditBalance(...args),
  claimBonus: vi.fn(),
}));

describe("useCredits", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchCreditBalance.mockResolvedValue({
      data: {
        balance: 100,
        bonus_eligible: false,
        next_bonus_at: null,
        is_admin: false,
        monthly_grant_available: false,
        monthly_grant_amount: 0,
      },
      errors: [],
    });
  });

  it("fetches balance on mount", async () => {
    renderHook(() => useCredits());
    await waitFor(() => {
      expect(mockFetchCreditBalance).toHaveBeenCalledTimes(1);
    });
  });

  it("refetches balance when credits:changed is dispatched", async () => {
    renderHook(() => useCredits());
    await waitFor(() => {
      expect(mockFetchCreditBalance).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      window.dispatchEvent(new Event(CREDITS_CHANGED_EVENT));
    });

    await waitFor(() => {
      expect(mockFetchCreditBalance).toHaveBeenCalledTimes(2);
    });
  });

  it("does not refetch after unmount when the event fires", async () => {
    const { unmount } = renderHook(() => useCredits());
    await waitFor(() => {
      expect(mockFetchCreditBalance).toHaveBeenCalledTimes(1);
    });

    unmount();

    await act(async () => {
      window.dispatchEvent(new Event(CREDITS_CHANGED_EVENT));
    });

    expect(mockFetchCreditBalance).toHaveBeenCalledTimes(1);
  });

  it("handles multiple rapid events without crashing, triggering a fetch each", async () => {
    renderHook(() => useCredits());
    await waitFor(() => {
      expect(mockFetchCreditBalance).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      window.dispatchEvent(new Event(CREDITS_CHANGED_EVENT));
      window.dispatchEvent(new Event(CREDITS_CHANGED_EVENT));
      window.dispatchEvent(new Event(CREDITS_CHANGED_EVENT));
    });

    await waitFor(() => {
      expect(mockFetchCreditBalance).toHaveBeenCalledTimes(4);
    });
  });
});
