import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import {
  fetchWishlist,
  markWishlistAcquired,
  removeFromWishlist,
} from "../api/wishlist";
import { Breadcrumb } from "../components/Breadcrumb";
import { CardImage } from "../components/CardImage";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { useRoutePrefix } from "../contexts/RoutePrefixContext";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";
import type { WishlistItem } from "../types/wishlist";

type Tab = "wanted" | "acquired";

export function WishlistPage() {
  const { t } = useTranslation();
  const prefix = useRoutePrefix();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("wanted");
  const [search, setSearch] = useState("");

  const wantedFetcher = useCallback(
    () =>
      fetchWishlist({
        acquired: "false",
        limit: "200",
        ...(search ? { search } : {}),
      }),
    [search],
  );

  const acquiredFetcher = useCallback(
    () =>
      fetchWishlist({
        acquired: "true",
        limit: "200",
        ...(search ? { search } : {}),
      }),
    [search],
  );

  const {
    data: wantedItems,
    loading: wantedLoading,
    refetch: refetchWanted,
  } = useApi<WishlistItem[]>(wantedFetcher, [search]);

  const {
    data: acquiredItems,
    loading: acquiredLoading,
    refetch: refetchAcquired,
  } = useApi<WishlistItem[]>(acquiredFetcher, [search]);

  const handleRemove = async (cardId: number) => {
    try {
      await removeFromWishlist(cardId);
      if (activeTab === "wanted") refetchWanted();
      else refetchAcquired();
    } catch {
      // Ignore
    }
  };

  const handleAcquire = async (cardId: number) => {
    try {
      await markWishlistAcquired(cardId);
      refetchWanted();
      refetchAcquired();
    } catch {
      // Ignore
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-slate-400">
        {t("wishlist.loginRequired")}
      </div>
    );
  }

  const breadcrumbs = [
    { label: t("nav.dashboard"), to: `${prefix}/` },
    { label: t("wishlist.title") },
  ];

  const tabs: { key: Tab; labelKey: string }[] = [
    { key: "wanted", labelKey: "wishlist.tabs.wanted" },
    { key: "acquired", labelKey: "wishlist.tabs.acquired" },
  ];

  const items = activeTab === "wanted" ? wantedItems : acquiredItems;
  const loading = activeTab === "wanted" ? wantedLoading : acquiredLoading;

  return (
    <div>
      <Breadcrumb items={breadcrumbs} />

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t("wishlist.title")}
        </h1>
      </div>

      {/* Search bar */}
      <div className="mb-4">
        <input
          type="text"
          placeholder={t("wishlist.searchPlaceholder")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-md px-4 py-2 rounded-lg bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid="wishlist-search"
        />
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-gray-200 dark:border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === tab.key
                ? "border-indigo-500 text-gray-900 dark:text-white"
                : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white"
            }`}
            data-testid={`tab-${tab.key}`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {loading && <LoadingSpinner message={t("common.loading")} />}

      {!loading && (!items || items.length === 0) && (
        <EmptyState
          title={
            activeTab === "wanted"
              ? t("wishlist.emptyWanted")
              : t("wishlist.emptyAcquired")
          }
          description={
            activeTab === "wanted"
              ? t("wishlist.emptyWantedDesc")
              : t("wishlist.emptyAcquiredDesc")
          }
          actions={
            activeTab === "wanted"
              ? [
                  {
                    label: t("wishlist.browseCatalog"),
                    onClick: () => navigate(`${prefix}/catalog`),
                  },
                ]
              : []
          }
        />
      )}

      {!loading && items && items.length > 0 && (
        <div
          className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
          data-testid="wishlist-grid"
        >
          {items.map((item) => (
            <WishlistCard
              key={item.id}
              item={item}
              onRemove={handleRemove}
              onAcquire={handleAcquire}
              isAcquired={activeTab === "acquired"}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function WishlistCard({
  item,
  onRemove,
  onAcquire,
  isAcquired,
}: {
  item: WishlistItem;
  onRemove: (cardId: number) => void;
  onAcquire: (cardId: number) => void;
  isAcquired: boolean;
}) {
  const { t } = useTranslation();

  const imgSrc =
    item.image_uri ??
    (item.set_code && item.collector_number
      ? scryfallImageUrl(item.set_code, item.collector_number, "normal")
      : item.name_en
        ? scryfallImageByName(item.name_en, "normal")
        : null);

  return (
    <div
      className="relative flex flex-col bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden"
      data-testid="wishlist-card"
    >
      {/* Card image */}
      <div className="aspect-[5/7] bg-gray-100 dark:bg-slate-700">
        <CardImage
          src={imgSrc}
          alt={item.name_en}
          className="w-full h-full object-cover"
        />
      </div>

      {/* Card info */}
      <div className="p-2 flex-1">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
          {item.name_en}
        </p>
        {item.set_code && (
          <p className="text-xs text-gray-500 dark:text-slate-400 uppercase">
            {item.set_code}
            {item.collector_number ? ` #${item.collector_number}` : ""}
          </p>
        )}
        {item.notes && (
          <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 truncate">
            {item.notes}
          </p>
        )}
        {item.max_price !== null && (
          <p className="text-xs text-indigo-500 dark:text-indigo-400 mt-0.5">
            {t("wishlist.maxPrice")}: R$ {item.max_price.toFixed(2)}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex border-t border-gray-200 dark:border-slate-700">
        {!isAcquired && (
          <button
            onClick={() => onAcquire(item.card_id)}
            className="flex-1 p-2 text-xs text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
            title={t("wishlist.markAcquired")}
            data-testid="acquire-button"
          >
            <svg
              className="h-4 w-4 mx-auto"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </button>
        )}
        <button
          onClick={() => onRemove(item.card_id)}
          className="flex-1 p-2 text-xs text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          title={t("common.delete")}
          data-testid="remove-button"
        >
          <svg
            className="h-4 w-4 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
