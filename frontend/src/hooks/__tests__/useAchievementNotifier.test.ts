import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAchievementNotifier } from "../useAchievementNotifier";

// Mock the API modules
vi.mock("../../api/achievements", () => ({
  checkAchievements: vi.fn(),
  fetchAchievements: vi.fn(),
}));

vi.mock("../../utils/creditsEvents", () => ({
  notifyCreditsChanged: vi.fn(),
}));

import { checkAchievements, fetchAchievements } from "../../api/achievements";
import { notifyCreditsChanged } from "../../utils/creditsEvents";

const mockCheck = vi.mocked(checkAchievements);
const mockFetch = vi.mocked(fetchAchievements);
const mockNotifyCreditsChanged = vi.mocked(notifyCreditsChanged);

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

  it("attaches reward per key and emits credits event once", async () => {
    mockCheck.mockResolvedValue({
      data: {
        newly_unlocked: ["first_card", "first_deck"],
        rewards: [
          { key: "first_card", amount: 50, tier: "common" },
          { key: "first_deck", amount: 100, tier: "uncommon" },
        ],
        total_reward: 150,
        backfilled: 0,
        balance: 150,
      },
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
          reward: 50,
          tier: "common",
          reward_credited: true,
        },
        {
          key: "first_deck",
          title: "First Deck",
          description: "Build your first deck",
          icon: "deck",
          unlocked: true,
          unlocked_at: "2026-09-06T00:00:00",
          reward: 100,
          tier: "uncommon",
          reward_credited: true,
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
      expect(result.current.toasts).toHaveLength(2);
    });

    const byKey = Object.fromEntries(
      result.current.toasts.map((t) => [t.title, t.reward]),
    );
    expect(byKey["First Card"]).toBe(50);
    expect(byKey["First Deck"]).toBe(100);
    expect(mockNotifyCreditsChanged).toHaveBeenCalledTimes(1);
  });

  it("does not attach a reward or emit an event when rewards are missing (old backend)", async () => {
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
          reward: 0,
          tier: null,
          reward_credited: false,
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

    expect(result.current.toasts[0].reward).toBeUndefined();
    expect(mockNotifyCreditsChanged).not.toHaveBeenCalled();
  });

  it("produces a single backfill toast when newly_unlocked is empty but backfilled > 0", async () => {
    mockCheck.mockResolvedValue({
      data: {
        newly_unlocked: [],
        backfilled: 300,
      },
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

    expect(result.current.toasts[0].reward).toBe(300);
    expect(result.current.toasts[0].icon).toBe("treasure");
    expect(mockFetch).not.toHaveBeenCalled();
    expect(mockNotifyCreditsChanged).toHaveBeenCalledTimes(1);
  });

  it("emits no credits event when nothing new and nothing backfilled", async () => {
    mockCheck.mockResolvedValue({
      data: { newly_unlocked: [], backfilled: 0, total_reward: 0 },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { result } = renderHook(() => useAchievementNotifier());

    await act(async () => {
      await result.current.checkAchievements();
    });

    expect(result.current.toasts).toHaveLength(0);
    expect(mockNotifyCreditsChanged).not.toHaveBeenCalled();
  });

  it("releases the checking lock after an error so the next call works", async () => {
    mockCheck.mockRejectedValueOnce(new Error("Network error"));
    mockCheck.mockResolvedValueOnce({
      data: { newly_unlocked: [], backfilled: 0 },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { result } = renderHook(() => useAchievementNotifier());

    await act(async () => {
      await result.current.checkAchievements();
    });
    await act(async () => {
      await result.current.checkAchievements();
    });

    expect(mockCheck).toHaveBeenCalledTimes(2);
  });
});
