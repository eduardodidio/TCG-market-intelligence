import { useEffect } from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useNavigate } from "react-router-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AchievementNotifierHost } from "../AchievementNotifierHost";

function Navigator({ to }: { to: string }) {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(to);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [to]);
  return null;
}

vi.mock("../../hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../../api/achievements", () => ({
  checkAchievements: vi.fn(),
  fetchAchievements: vi.fn(),
}));

import { useAuth } from "../../hooks/useAuth";
import { checkAchievements, fetchAchievements } from "../../api/achievements";

const mockUseAuth = vi.mocked(useAuth);
const mockCheck = vi.mocked(checkAchievements);
const mockFetch = vi.mocked(fetchAchievements);

const EMPTY_RESPONSE = {
  data: { newly_unlocked: [], backfilled: 0 },
  meta: { cursor: null, total: null, offset: null, request_id: "" },
  errors: [],
};

function renderHost(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="*" element={<AchievementNotifierHost />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AchievementNotifierHost", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockCheck.mockResolvedValue(EMPTY_RESPONSE as never);
    mockFetch.mockResolvedValue({
      data: [],
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });
    mockUseAuth.mockReturnValue({
      user: { role: "member" },
      isAuthenticated: true,
    } as never);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("calls checkAchievements on mount", async () => {
    renderHost();

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockCheck).toHaveBeenCalledTimes(1);
  });

  it("does not re-check within 30s of a route change, but does after", async () => {
    function Harness({ path }: { path: string }) {
      return (
        <MemoryRouter initialEntries={["/a"]}>
          <AchievementNotifierHost />
          <Navigator to={path} />
        </MemoryRouter>
      );
    }

    const { rerender } = render(<Harness path="/a" />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(mockCheck).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(10_000);
    });

    rerender(<Harness path="/b" />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(mockCheck).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(21_000);
    });

    rerender(<Harness path="/c" />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(mockCheck).toHaveBeenCalledTimes(2);
  });

  it("does not call checkAchievements for guests", async () => {
    mockUseAuth.mockReturnValue({
      user: { role: "guest" },
      isAuthenticated: true,
    } as never);

    renderHost();

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockCheck).not.toHaveBeenCalled();
  });

  it("does not call checkAchievements for anonymous users", async () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
    } as never);

    renderHost();

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockCheck).not.toHaveBeenCalled();
  });

  it("renders multiple stacked toasts without overlap markup collisions", async () => {
    vi.useRealTimers();
    mockCheck.mockResolvedValue({
      data: { newly_unlocked: ["first_card", "first_deck"], backfilled: 0 },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    } as never);
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

    renderHost();

    await waitFor(() => {
      expect(screen.getAllByTestId("achievement-toast")).toHaveLength(2);
    });
    expect(screen.getByTestId("achievement-notifier-host")).toBeInTheDocument();
  });

  it("dismissing one toast removes only that toast", async () => {
    vi.useRealTimers();
    mockCheck.mockResolvedValue({
      data: { newly_unlocked: ["first_card", "first_deck"], backfilled: 0 },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    } as never);
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

    renderHost();

    await waitFor(() => {
      expect(screen.getAllByTestId("achievement-toast")).toHaveLength(2);
    });

    const dismissButtons = screen.getAllByTestId("achievement-toast-dismiss");
    await act(async () => {
      dismissButtons[0].click();
    });

    await waitFor(
      () => {
        expect(screen.getAllByTestId("achievement-toast")).toHaveLength(1);
      },
      { timeout: 1000 },
    );
  });
});
