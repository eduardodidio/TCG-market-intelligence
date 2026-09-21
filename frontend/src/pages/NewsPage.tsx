import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingSpinner } from "../components/LoadingSpinner";
import {
  fetchNews,
  markNewsRead,
  markNewsUnread,
  type NewsItem,
  type NewsListResponse,
} from "../api/news";

type FilterTab = "unread" | "read" | "all";

const CATEGORIES = ["all", "ban", "release", "event", "reprint", "other"] as const;
const ITEMS_PER_PAGE = 20;

const CATEGORY_COLORS: Record<string, string> = {
  ban: "bg-red-500/20 text-red-400",
  release: "bg-green-500/20 text-green-400",
  event: "bg-blue-500/20 text-blue-400",
  reprint: "bg-purple-500/20 text-purple-400",
  other: "bg-gray-500/20 text-gray-400",
};

function formatRelativeDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHrs = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHrs / 24);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHrs < 24) return `${diffHrs}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function NewsPage() {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<FilterTab>("unread");
  const [category, setCategory] = useState<string>("all");
  const [offset, setOffset] = useState(0);

  const fetcher = useCallback(
    () =>
      fetchNews({
        filter,
        category: category !== "all" ? category : "",
        limit: String(ITEMS_PER_PAGE),
        offset: String(offset),
      }),
    [filter, category, offset],
  );

  const {
    data: newsData,
    loading,
    error,
    refetch,
  } = useApi<NewsListResponse>(fetcher, [filter, category, offset]);

  const items = newsData?.items ?? [];
  const total = newsData?.total ?? 0;
  const hasMore = offset + ITEMS_PER_PAGE < total;

  const handleItemClick = async (item: NewsItem) => {
    // Open in new tab
    window.open(item.source_url, "_blank", "noopener,noreferrer");
    // Mark as read
    if (!item.is_read) {
      try {
        await markNewsRead(item.id);
        refetch();
      } catch {
        // Ignore
      }
    }
  };

  const handleMarkUnread = async (e: React.MouseEvent, itemId: number) => {
    e.stopPropagation();
    try {
      await markNewsUnread(itemId);
      refetch();
    } catch {
      // Ignore
    }
  };

  const handleFilterChange = (newFilter: FilterTab) => {
    setFilter(newFilter);
    setOffset(0);
  };

  const handleCategoryChange = (newCategory: string) => {
    setCategory(newCategory);
    setOffset(0);
  };

  const breadcrumbs = [
    { label: t("nav.dashboard"), to: "/" },
    { label: t("news.title") },
  ];

  const tabs: { key: FilterTab; labelKey: string }[] = [
    { key: "unread", labelKey: "news.filterUnread" },
    { key: "read", labelKey: "news.filterRead" },
    { key: "all", labelKey: "news.filterAll" },
  ];

  return (
    <div>
      <Breadcrumb items={breadcrumbs} />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        {t("news.title")}
      </h1>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200 dark:border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleFilterChange(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              filter === tab.key
                ? "border-indigo-500 text-gray-900 dark:text-white"
                : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white"
            }`}
            data-testid={`filter-tab-${tab.key}`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => handleCategoryChange(cat)}
            className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
              category === cat
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 hover:bg-gray-200 dark:hover:bg-slate-600"
            }`}
            data-testid={`category-${cat}`}
          >
            {t(`news.category_${cat}`)}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Loading state */}
      {loading && <LoadingSpinner message={t("common.loading")} />}

      {/* Empty state */}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title={t("news.emptyTitle")}
          description={t("news.emptyDescription")}
        />
      )}

      {/* News cards grid */}
      {!loading && items.length > 0 && (
        <>
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            data-testid="news-grid"
          >
            {items.map((item) => (
              <article
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={`group cursor-pointer rounded-lg border transition-all duration-200 overflow-hidden ${
                  item.is_read
                    ? "bg-gray-50 dark:bg-slate-800/50 border-gray-200 dark:border-slate-700/50 opacity-75"
                    : "bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-500 hover:shadow-md"
                }`}
                data-testid="news-card"
              >
                {/* Image */}
                {item.image_url && (
                  <div className="h-40 overflow-hidden">
                    <img
                      src={item.image_url}
                      alt=""
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </div>
                )}
                <div className="p-4">
                  {/* Source + Category badges */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium text-gray-500 dark:text-slate-400">
                      {item.source_name}
                    </span>
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                        CATEGORY_COLORS[item.category] ?? CATEGORY_COLORS.other
                      }`}
                    >
                      {t(`news.category_${item.category}`)}
                    </span>
                  </div>

                  {/* Title */}
                  <h3
                    className={`text-sm leading-snug mb-2 line-clamp-2 ${
                      item.is_read
                        ? "font-normal text-gray-600 dark:text-slate-400"
                        : "font-bold text-gray-900 dark:text-white"
                    }`}
                  >
                    {item.title}
                  </h3>

                  {/* Summary */}
                  {item.summary && (
                    <p className="text-xs text-gray-500 dark:text-slate-400 line-clamp-3 mb-3">
                      {item.summary}
                    </p>
                  )}

                  {/* Footer: date + mark unread */}
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400 dark:text-slate-500">
                      {formatRelativeDate(item.published_at)}
                    </span>
                    {item.is_read && (
                      <button
                        onClick={(e) => handleMarkUnread(e, item.id)}
                        className="text-xs text-indigo-500 dark:text-indigo-400 hover:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
                        data-testid="mark-unread-button"
                      >
                        {t("news.markUnread")}
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6">
            <p className="text-sm text-gray-500 dark:text-slate-400">
              {t("news.showing", {
                from: offset + 1,
                to: Math.min(offset + ITEMS_PER_PAGE, total),
                total,
              })}
            </p>
            <div className="flex gap-2">
              {offset > 0 && (
                <button
                  onClick={() => setOffset(Math.max(0, offset - ITEMS_PER_PAGE))}
                  className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 rounded-md hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                  data-testid="prev-page"
                >
                  {t("common.prev")}
                </button>
              )}
              {hasMore && (
                <button
                  onClick={() => setOffset(offset + ITEMS_PER_PAGE)}
                  className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-500 transition-colors"
                  data-testid="next-page"
                >
                  {t("common.next")}
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
