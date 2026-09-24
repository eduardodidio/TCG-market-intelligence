import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NewsPage } from "../NewsPage";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        "common.loading": "Loading...",
        "common.prev": "Previous",
        "common.next": "Next",
        "common.retry": "Retry",
        "nav.dashboard": "Dashboard",
        "news.title": "MTG News",
        "news.filterUnread": "Unread",
        "news.filterRead": "Read",
        "news.filterAll": "All",
        "news.category_all": "All",
        "news.category_ban": "Bans",
        "news.category_release": "Releases",
        "news.category_event": "Events",
        "news.category_reprint": "Reprints",
        "news.category_other": "Other",
        "news.emptyTitle": "No news yet",
        "news.emptyDescription":
          "News will appear here after the feed is fetched.",
        "news.errorTitle": "Could not load news",
        "news.noDataTitle": "No news collected yet",
        "news.noDataDescription": "No news has been collected yet.",
        "news.allReadTitle": "You're all caught up!",
        "news.allReadDescription": "There are no unread news items.",
        "news.showAll": "Show all",
        "news.filterEmptyTitle": "No news matches this filter",
        "news.clearFilters": "Clear filters",
        "news.lastUpdated": `Last collected: ${opts?.date ?? ""}`,
        "news.stale": "stale",
        "news.markUnread": "Mark unread",
        "news.showing": `Showing ${opts?.from ?? ""}-${opts?.to ?? ""} of ${opts?.total ?? ""}`,
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock the API
vi.mock("../../api/news", () => ({
  fetchNews: vi.fn(),
  fetchNewsStatus: vi.fn(),
  markNewsRead: vi.fn(),
  markNewsUnread: vi.fn(),
  fetchUnreadCount: vi.fn(),
}));

import {
  fetchNews,
  fetchNewsStatus,
  markNewsRead,
  markNewsUnread,
} from "../../api/news";

const mockFetchNews = vi.mocked(fetchNews);
const mockFetchNewsStatus = vi.mocked(fetchNewsStatus);
const mockMarkRead = vi.mocked(markNewsRead);
const mockMarkUnread = vi.mocked(markNewsUnread);

const MOCK_NEWS_ITEMS = [
  {
    id: 1,
    title: "Card X Banned in Modern",
    summary: "Wizards has banned Card X from Modern format.",
    source_url: "https://example.com/ban-news",
    source_name: "MTG Official",
    category: "ban",
    image_url: "https://example.com/img.jpg",
    published_at: "2026-09-21T12:00:00",
    fetched_at: "2026-09-21T12:30:00",
    is_read: false,
  },
  {
    id: 2,
    title: "New Set Preview: Aether Revolt",
    summary: "Preview season begins for the new set.",
    source_url: "https://example.com/preview",
    source_name: "Scryfall Blog",
    category: "release",
    image_url: null,
    published_at: "2026-09-20T10:00:00",
    fetched_at: "2026-09-21T12:30:00",
    is_read: true,
  },
];

function statusResponse(overrides?: Partial<{
  total_items: number;
  last_fetched_at: string | null;
  newest_published_at: string | null;
}>) {
  return {
    data: {
      total_items: 2,
      last_fetched_at: "2026-09-21T12:30:00",
      newest_published_at: "2026-09-21T12:00:00",
      ...overrides,
    },
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <NewsPage />
    </MemoryRouter>,
  );
}

describe("NewsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Sane default so tests that don't care about status still work
    mockFetchNewsStatus.mockResolvedValue(statusResponse());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows loading state", () => {
    mockFetchNews.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders news items", async () => {
    mockFetchNews.mockResolvedValue({
      data: { items: MOCK_NEWS_ITEMS, total: 2 },
      meta: { cursor: null, total: 2, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("Card X Banned in Modern"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("New Set Preview: Aether Revolt"),
      ).toBeInTheDocument();
    });
  });

  it("shows no-data state when nothing has been collected", async () => {
    mockFetchNewsStatus.mockResolvedValue(
      statusResponse({ total_items: 0, last_fetched_at: null, newest_published_at: null }),
    );
    mockFetchNews.mockResolvedValue({
      data: { items: [], total: 0 },
      meta: { cursor: null, total: 0, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("news-no-data")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("filter-tab-unread")).not.toBeInTheDocument();
    expect(screen.queryByTestId("category-all")).not.toBeInTheDocument();
  });

  it("shows all-read state and switches to All on show-all click", async () => {
    mockFetchNewsStatus.mockResolvedValue(statusResponse({ total_items: 5 }));
    mockFetchNews.mockResolvedValue({
      data: { items: [], total: 0 },
      meta: { cursor: null, total: 0, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("news-all-read")).toBeInTheDocument();
    });

    mockFetchNews.mockClear();
    fireEvent.click(screen.getByTestId("news-show-all"));

    await waitFor(() => {
      expect(mockFetchNews).toHaveBeenCalledWith(
        expect.objectContaining({ filter: "all" }),
      );
    });
  });

  it("shows filter-empty state and clears filters", async () => {
    mockFetchNewsStatus.mockResolvedValue(statusResponse({ total_items: 5 }));
    mockFetchNews.mockResolvedValue({
      data: { items: [], total: 0 },
      meta: { cursor: null, total: 0, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("filter-tab-all")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("filter-tab-all"));
    await waitFor(() => {
      expect(screen.getByTestId("category-ban")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("category-ban"));

    await waitFor(() => {
      expect(screen.getByTestId("news-filter-empty")).toBeInTheDocument();
    });

    mockFetchNews.mockClear();
    fireEvent.click(screen.getByTestId("news-clear-filters"));

    await waitFor(() => {
      expect(mockFetchNews).toHaveBeenCalledWith(
        expect.objectContaining({ filter: "all", category: "" }),
      );
    });
  });

  it("shows error banner on fetch failure and retries", async () => {
    mockFetchNews.mockRejectedValue(new Error("boom"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeInTheDocument();
    });

    mockFetchNews.mockClear();
    mockFetchNews.mockResolvedValue({
      data: { items: MOCK_NEWS_ITEMS, total: 2 },
      meta: { cursor: null, total: 2, offset: null, request_id: "test" },
      errors: [],
    });
    fireEvent.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(mockFetchNews).toHaveBeenCalled();
    });
  });

  it("shows the grid and hides freshness line when status fetch fails", async () => {
    mockFetchNewsStatus.mockRejectedValue(new Error("status down"));
    mockFetchNews.mockResolvedValue({
      data: { items: MOCK_NEWS_ITEMS, total: 2 },
      meta: { cursor: null, total: 2, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("news-grid")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("error-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("news-last-updated")).not.toBeInTheDocument();
  });

  it("does not mark the freshness line as stale at 71 hours", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-09-24T00:00:00Z"));

    mockFetchNewsStatus.mockResolvedValue(
      statusResponse({ last_fetched_at: "2026-09-21T01:00:00Z" }), // 71h ago
    );
    mockFetchNews.mockResolvedValue({
      data: { items: MOCK_NEWS_ITEMS, total: 2 },
      meta: { cursor: null, total: 2, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("news-last-updated")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("news-stale")).not.toBeInTheDocument();
  });

  it("marks the freshness line as stale at 73 hours", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-09-24T00:00:00Z"));

    mockFetchNewsStatus.mockResolvedValue(
      statusResponse({ last_fetched_at: "2026-09-20T23:00:00Z" }), // 73h ago
    );
    mockFetchNews.mockResolvedValue({
      data: { items: MOCK_NEWS_ITEMS, total: 2 },
      meta: { cursor: null, total: 2, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("news-stale")).toBeInTheDocument();
    });
  });

  it("renders filter tabs", async () => {
    mockFetchNewsStatus.mockResolvedValue(statusResponse({ total_items: 5 }));
    mockFetchNews.mockResolvedValue({
      data: { items: [], total: 0 },
      meta: { cursor: null, total: 0, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("filter-tab-unread")).toBeInTheDocument();
      expect(screen.getByTestId("filter-tab-read")).toBeInTheDocument();
      expect(screen.getByTestId("filter-tab-all")).toBeInTheDocument();
    });
  });

  it("changes filter on tab click", async () => {
    mockFetchNewsStatus.mockResolvedValue(statusResponse({ total_items: 5 }));
    mockFetchNews.mockResolvedValue({
      data: { items: [], total: 0 },
      meta: { cursor: null, total: 0, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("filter-tab-all")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("filter-tab-all"));

    // Should have called fetchNews again with filter=all
    await waitFor(() => {
      expect(mockFetchNews).toHaveBeenCalled();
    });
  });

  it("opens link in new tab and marks as read on click", async () => {
    mockFetchNews.mockResolvedValue({
      data: { items: [MOCK_NEWS_ITEMS[0]], total: 1 },
      meta: { cursor: null, total: 1, offset: null, request_id: "test" },
      errors: [],
    });
    mockMarkRead.mockResolvedValue({
      data: { marked: true },
      meta: { cursor: null, total: null, offset: null, request_id: "test" },
      errors: [],
    });

    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("Card X Banned in Modern"),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("news-card"));

    expect(openSpy).toHaveBeenCalledWith(
      "https://example.com/ban-news",
      "_blank",
      "noopener,noreferrer",
    );
    expect(mockMarkRead).toHaveBeenCalledWith(1);

    openSpy.mockRestore();
  });

  it("shows mark unread button for read items", async () => {
    mockFetchNews.mockResolvedValue({
      data: { items: [MOCK_NEWS_ITEMS[1]], total: 1 },
      meta: { cursor: null, total: 1, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("mark-unread-button")).toBeInTheDocument();
    });
  });

  it("calls markNewsUnread when mark unread button clicked", async () => {
    mockFetchNews.mockResolvedValue({
      data: { items: [MOCK_NEWS_ITEMS[1]], total: 1 },
      meta: { cursor: null, total: 1, offset: null, request_id: "test" },
      errors: [],
    });
    mockMarkUnread.mockResolvedValue({
      data: { marked: true },
      meta: { cursor: null, total: null, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("mark-unread-button")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("mark-unread-button"));
    expect(mockMarkUnread).toHaveBeenCalledWith(2);
  });

  it("renders category filter buttons", async () => {
    mockFetchNewsStatus.mockResolvedValue(statusResponse({ total_items: 5 }));
    mockFetchNews.mockResolvedValue({
      data: { items: [], total: 0 },
      meta: { cursor: null, total: 0, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("category-all")).toBeInTheDocument();
      expect(screen.getByTestId("category-ban")).toBeInTheDocument();
      expect(screen.getByTestId("category-release")).toBeInTheDocument();
    });
  });

  it("shows pagination when there are more items", async () => {
    mockFetchNews.mockResolvedValue({
      data: { items: MOCK_NEWS_ITEMS, total: 30 },
      meta: { cursor: null, total: 30, offset: null, request_id: "test" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("next-page")).toBeInTheDocument();
    });
  });
});
