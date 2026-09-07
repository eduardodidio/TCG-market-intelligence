import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAchievementNotifier } from "../useAchievementNotifier";

// Mock the API modules
vi.mock("../../api/achievements", () => ({
  checkAchievements: vi.fn(),
  fetchAchievements: vi.fn(),
}));

import { checkAchievements, fetchAchievements } from "../../api/achievements";

const mockCheck = vi.mocked(checkAchievements);
const mockFetch = vi.mocked(fetchAchievements);

describe("useAchievementNotifier", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with empty toasts", () => {
    const { result } = renderHook(() => useAchievementNotifier());
    expect(result.current.toasts).toHaveLength(0);
  });

  it("adds toasts when achievements are unlocked", async () => {
    mockCheck.mockResolvedValue({
      data: { newly_unlocked: ["first_card"] },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });
    mockFetch.mockResolvedValue({
      data: [
        {
          key: "first_card",
          title: "First Card",
          description: "Add your first card",
          icon: "card",
          unlocked: true,
          unlocked_at: "2026-09-06T00:00:00",
        },
      ],
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { result } = renderHook(() => useAchievementNotifier());

    await act(async () => {
      await result.current.checkAchievements();
    });

    await waitFor(() => {
      expect(result.current.toasts).toHaveLength(1);
      expect(result.current.toasts[0].title).toBe("First Card");
    });
  });

  it("does not add toasts when no achievements unlocked", async () => {
    mockCheck.mockResolvedValue({
      data: { newly_unlocked: [] },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { result } = renderHook(() => useAchievementNotifier());

    await act(async () => {
      await result.current.checkAchievements();
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it("can dismiss toasts", async () => {
    mockCheck.mockResolvedValue({
      data: { newly_unlocked: ["first_card"] },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });
    mockFetch.mockResolvedValue({
      data: [
        {
          key: "first_card",
          title: "First Card",
          description: "Add your first card",
          icon: "card",
          unlocked: true,
          unlocked_at: "2026-09-06T00:00:00",
        },
      ],
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { result } = renderHook(() => useAchievementNotifier());

    await act(async () => {
      await result.current.checkAchievements();
    });

    await waitFor(() => {
      expect(result.current.toasts).toHaveLength(1);
    });

    const toastId = result.current.toasts[0].id;
    act(() => {
      result.current.dismissToast(toastId);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it("handles API errors gracefully", async () => {
    mockCheck.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useAchievementNotifier());

    await act(async () => {
      await result.current.checkAchievements();
    });

    // Should not throw, toasts stay empty
    expect(result.current.toasts).toHaveLength(0);
  });
});
