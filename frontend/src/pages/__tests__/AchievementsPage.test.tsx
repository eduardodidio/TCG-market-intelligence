import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AchievementsPage } from "../AchievementsPage";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        "common.loading": "Loading...",
        "nav.dashboard": "Dashboard",
        "achievements.pageTitle": "Achievements",
        "achievements.progress": `${opts?.unlocked ?? 0} / ${opts?.total ?? 0} achievements unlocked`,
        "achievements.locked": "Keep playing to unlock",
        "achievements.unlockedAt": `Unlocked on ${opts?.date ?? ""}`,
        "achievements.reward": `+${opts?.amount ?? 0} Treasures`,
        "achievements.rewardEarned": "Earned",
        "achievements.treasureProgress": `${opts?.earned ?? 0} / ${opts?.total ?? 0} Treasures earned`,
        "achievements.tier.common": "Common",
        "achievements.tier.uncommon": "Uncommon",
        "achievements.tier.rare": "Rare",
        "achievements.tier.mythic": "Mythic",
        "achievements.tier.legendary": "Legendary",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock the API
vi.mock("../../api/achievements", () => ({
  fetchAchievements: vi.fn(),
}));

import { fetchAchievements } from "../../api/achievements";

const mockFetch = vi.mocked(fetchAchievements);

const MOCK_ACHIEVEMENTS = [
  {
    key: "first_card",
    title: "First Card",
    description: "Add your first card",
    icon: "card",
    unlocked: true,
    unlocked_at: "2026-09-06T00:00:00",
  },
  {
    key: "deck_builder",
    title: "Deck Builder",
    description: "Create your first deck",
    icon: "deck",
    unlocked: false,
    unlocked_at: null,
  },
  {
    key: "scanner",
    title: "Scanner",
    description: "Complete first scan",
    icon: "scan",
    unlocked: false,
    unlocked_at: null,
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <AchievementsPage />
    </MemoryRouter>,
  );
}

describe("AchievementsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders achievements grid", async () => {
    mockFetch.mockResolvedValue({
      data: MOCK_ACHIEVEMENTS,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("achievements-page")).toBeInTheDocument();
    });

    expect(screen.getByTestId("achievements-grid")).toBeInTheDocument();
    expect(screen.getByTestId("achievement-card-first_card")).toBeInTheDocument();
    expect(screen.getByTestId("achievement-card-deck_builder")).toBeInTheDocument();
  });

  it("shows progress bar", async () => {
    mockFetch.mockResolvedValue({
      data: MOCK_ACHIEVEMENTS,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("achievements-progress")).toBeInTheDocument();
    });

    // 1 out of 3 unlocked
    expect(screen.getByText("1 / 3 achievements unlocked")).toBeInTheDocument();
  });

  it("shows unlocked achievement with icon and description", async () => {
    mockFetch.mockResolvedValue({
      data: MOCK_ACHIEVEMENTS,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("First Card")).toBeInTheDocument();
    });

    expect(screen.getByText("Add your first card")).toBeInTheDocument();
  });

  it("shows locked achievement with hidden description", async () => {
    mockFetch.mockResolvedValue({
      data: MOCK_ACHIEVEMENTS,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Deck Builder")).toBeInTheDocument();
    });

    // Locked achievement shows "Keep playing to unlock" instead of description
    expect(screen.getAllByText("Keep playing to unlock").length).toBeGreaterThan(0);
  });

  it("shows error state", async () => {
    mockFetch.mockResolvedValue({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code: "HTTP_500", message: "Server error" }],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("renders breadcrumb navigation", async () => {
    mockFetch.mockResolvedValue({
      data: MOCK_ACHIEVEMENTS,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("breadcrumb")).toBeInTheDocument();
    });
  });

  describe("reward chips and treasure totals", () => {
    const REWARD_ACHIEVEMENTS = [
      {
        key: "common_win",
        title: "Common Win",
        description: "Do a common thing",
        icon: "card",
        unlocked: true,
        unlocked_at: "2026-09-06T00:00:00",
        reward: 50,
        tier: "common",
        reward_credited: true,
      },
      {
        key: "rare_win",
        title: "Rare Win",
        description: "Do a rare thing",
        icon: "deck",
        unlocked: false,
        unlocked_at: null,
        reward: 250,
        tier: "rare",
        reward_credited: false,
      },
      {
        key: "legendary_win",
        title: "Legendary Win",
        description: "Do a legendary thing",
        icon: "trophy",
        unlocked: false,
        unlocked_at: null,
        reward: 1000,
        tier: "legendary",
        reward_credited: false,
      },
    ];

    it("shows reward chips with tier labels and correct totals", async () => {
      mockFetch.mockResolvedValue({
        data: REWARD_ACHIEVEMENTS,
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [],
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId("achievement-reward-common_win")).toBeInTheDocument();
      });

      expect(screen.getByTestId("achievement-reward-common_win")).toHaveTextContent(
        "+50 Treasures",
      );
      expect(screen.getByTestId("achievement-reward-rare_win")).toHaveTextContent(
        "+250 Treasures",
      );
      expect(screen.getByTestId("achievement-reward-legendary_win")).toHaveTextContent(
        "+1000 Treasures",
      );

      expect(
        screen.getByTestId("achievement-reward-earned-common_win"),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId("achievement-reward-earned-rare_win"),
      ).not.toBeInTheDocument();

      expect(screen.getByTestId("achievements-treasure-progress")).toHaveTextContent(
        "50 / 1300 Treasures earned",
      );
    });

    it("does not render a chip or crash for items without a reward field", async () => {
      mockFetch.mockResolvedValue({
        data: MOCK_ACHIEVEMENTS,
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [],
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId("achievements-page")).toBeInTheDocument();
      });

      expect(
        screen.queryByTestId("achievement-reward-first_card"),
      ).not.toBeInTheDocument();
      expect(screen.getByTestId("achievements-treasure-progress")).toHaveTextContent(
        "0 / 0 Treasures earned",
      );
    });

    it("shows a chip without a tier label when tier is null", async () => {
      mockFetch.mockResolvedValue({
        data: [
          {
            key: "no_tier",
            title: "No Tier",
            description: "Reward without tier",
            icon: "star",
            unlocked: false,
            unlocked_at: null,
            reward: 100,
            tier: null,
            reward_credited: false,
          },
        ],
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [],
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId("achievement-reward-no_tier")).toBeInTheDocument();
      });

      const chip = screen.getByTestId("achievement-reward-no_tier");
      expect(chip).toHaveTextContent("+100 Treasures");
      expect(chip.textContent).not.toContain("·");
    });

    it("does not show an earned marker when unlocked but reward not credited", async () => {
      mockFetch.mockResolvedValue({
        data: [
          {
            key: "not_credited",
            title: "Not Credited",
            description: "Unlocked but not credited",
            icon: "star",
            unlocked: true,
            unlocked_at: "2026-09-06T00:00:00",
            reward: 75,
            tier: "common",
            reward_credited: false,
          },
        ],
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [],
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId("achievement-reward-not_credited")).toBeInTheDocument();
      });

      expect(
        screen.queryByTestId("achievement-reward-earned-not_credited"),
      ).not.toBeInTheDocument();
    });

    it("shows earned equal to total when all achievements are unlocked and credited", async () => {
      mockFetch.mockResolvedValue({
        data: REWARD_ACHIEVEMENTS.map((a) => ({
          ...a,
          unlocked: true,
          reward_credited: true,
        })),
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [],
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId("achievements-treasure-progress")).toBeInTheDocument();
      });

      expect(screen.getByTestId("achievements-treasure-progress")).toHaveTextContent(
        "1300 / 1300 Treasures earned",
      );
    });

    it("shows 0 / 0 totals for an empty achievement list", async () => {
      mockFetch.mockResolvedValue({
        data: [],
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [],
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId("achievements-treasure-progress")).toBeInTheDocument();
      });

      expect(screen.getByTestId("achievements-treasure-progress")).toHaveTextContent(
        "0 / 0 Treasures earned",
      );
    });
  });
});
