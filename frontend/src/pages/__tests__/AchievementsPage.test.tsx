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
});
