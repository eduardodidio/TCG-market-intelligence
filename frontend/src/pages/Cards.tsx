import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { fetchCards, searchCardsWeb } from "../api/cards";
import { fetchSets } from "../api/sets";
import { apiPost } from "../api/client";
import { createEvaluation } from "../api/evaluations";
import { CardTile } from "../components/CardTile";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FilterChips } from "../components/FilterChips";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/Skeleton";
import { SortSelect, EXPLORE_SORT_OPTIONS } from "../components/SortSelect";
import { useAuth } from "../hooks/useAuth";
import { useCurrency } from "../hooks/useCurrency";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import type { CardSummary, SetSummary, WebSearchResult } from "../types/api";
import { DEFAULT_PAGE_LIMIT } from "../utils/constants";

type SearchMode = "local" | "web";

export function Cards() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    document.title = `${t("cards.title")} | TCG Market`;
  }, [t]);

  const { currency } = useCurrency();
  const [searchParams, setSearchParams] = useSearchParams();

  // Shared state
  const [mode, setMode] = useState<SearchMode>("local");

  // Local search state
  const [searchTerm, setSearchTerm] = useState(
    searchParams.get("name") ?? "",
  );
  const [selectedSet, setSelectedSet] = useState<string | null>(
    searchParams.get("set") ?? null,
  );
  const [sortBy, setSortBy] = useState(searchParams.get("sort") ?? "name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">((searchParams.get("dir") as "asc" | "desc") ?? "asc");
  const [cards, setCards] = useState<CardSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sets, setSets] = useState<SetSummary[]>([]);

  // Web search state
  const [webQuery, setWebQuery] = useState("");
  const [webResults, setWebResults] = useState<WebSearchResult[]>([]);
  const [webLoading, setWebLoading] = useState(false);
  const [webError, setWebError] = useState<string | null>(null);
  const [webSearched, setWebSearched] = useState(false);
  const [cooldown, setCooldown] = useState(false);
  const [addingIdx, setAddingIdx] = useState<number | null>(null);
  const [addedIdxs, setAddedIdxs] = useState<Set<number>>(new Set());
  const [evalAddingIdx, setEvalAddingIdx] = useState<number | null>(null);
  const [evalAddedIdxs, setEvalAddedIdxs] = useState<Set<number>>(new Set());

  const debouncedSearch = useDebounce(searchTerm, 300);
  const fetchIdRef = useRef(0);

  // Load sets on mount
  useEffect(() => {
    fetchSets()
      .then((res) => {
        if (res.data) setSets(res.data);
      })
      .catch(() => {
        setError(t("cards.setsLoadError"));
      });
  }, [t]);

  // Sync search params to URL (local mode only)
  useEffect(() => {
    if (mode !== "local") return;
    const params: Record<string, string> = {};
    if (debouncedSearch) params.name = debouncedSearch;
    if (selectedSet) params.set = selectedSet;
    if (sortBy !== "name") params.sort = sortBy;
    if (sortDir !== "asc") params.dir = sortDir;
    setSearchParams(params, { replace: true });
  }, [debouncedSearch, selectedSet, sortBy, sortDir, setSearchParams, mode]);

  // Fetch cards when filters change (local mode)
  useEffect(() => {
    if (mode !== "local") return;

    fetchIdRef.current += 1;
    const currentFetchId = fetchIdRef.current;

    setLoading(true);
    setError(null);
    setCursor(null);
    setCards([]);

    const params: Record<string, string> = {
      limit: String(DEFAULT_PAGE_LIMIT),
      currency,
    };
    if (debouncedSearch) params.name = debouncedSearch;
    if (selectedSet) params.set = selectedSet;
    if (sortBy !== "price") {
      params.sort_by = sortBy;
      params.sort_dir = sortDir;
    }

    fetchCards(params)
      .then((res) => {
        if (currentFetchId !== fetchIdRef.current) return;
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else {
          setCards(res.data ?? []);
          setCursor(res.meta.cursor);
        }
      })
      .catch((err: unknown) => {
        if (currentFetchId !== fetchIdRef.current) return;
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      })
      .finally(() => {
        if (currentFetchId === fetchIdRef.current) {
          setLoading(false);
        }
      });
  }, [debouncedSearch, selectedSet, sortBy, sortDir, currency, mode]);

  // Load more handler (local mode)
  const handleLoadMore = useCallback(() => {
    if (!cursor || loadingMore) return;

    setLoadingMore(true);
    const params: Record<string, string> = {
      limit: String(DEFAULT_PAGE_LIMIT),
      cursor,
      currency,
    };
    if (debouncedSearch) params.name = debouncedSearch;
    if (selectedSet) params.set = selectedSet;
    if (sortBy !== "price") {
      params.sort_by = sortBy;
      params.sort_dir = sortDir;
    }

    fetchCards(params)
      .then((res) => {
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else {
          setCards((prev) => [...prev, ...(res.data ?? [])]);
          setCursor(res.meta.cursor);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      })
      .finally(() => {
        setLoadingMore(false);
      });
  }, [cursor, loadingMore, debouncedSearch, selectedSet, sortBy, sortDir, currency]);

  const setOptions = sets.map((s) => ({
    label: s.set_code,
    value: s.set_code,
  }));

  const sentinelRef = useInfiniteScroll(handleLoadMore, {
    enabled: !!cursor && !loadingMore,
  });

  const handleClearFilters = useCallback(() => {
    setSearchTerm("");
    setSelectedSet(null);
  }, []);

  const handleSortChange = useCallback((newSortBy: string, newSortDir: "asc" | "desc") => {
    setSortBy(newSortBy);
    setSortDir(newSortDir);
  }, []);

  // Web search handler
  const handleWebSearch = useCallback(async () => {
    if (!webQuery.trim() || cooldown || webLoading) return;

    setWebLoading(true);
    setWebError(null);
    setWebSearched(true);
    setWebResults([]);
    setAddedIdxs(new Set());

    try {
      const res = await searchCardsWeb(webQuery.trim());
      if (res.errors.length > 0) {
        const firstError = res.errors[0];
        if (firstError.code === "HTTP_402") {
          setWebError(t("credits.insufficient") || "Insufficient credits");
        } else if (firstError.code === "HTTP_503") {
          setWebError(t("cards.ligaUnavailable"));
        } else {
          setWebError(firstError.message);
        }
      } else {
        setWebResults(res.data ?? []);
      }
    } catch (err: unknown) {
      setWebError(err instanceof Error ? err.message : t("common.unknownError"));
    } finally {
      setWebLoading(false);
      // Start cooldown
      setCooldown(true);
      setTimeout(() => setCooldown(false), 3000);
    }
  }, [webQuery, cooldown, webLoading, t]);

  // Add to collection handler
  const handleAddToCollection = useCallback(async (result: WebSearchResult, idx: number) => {
    setAddingIdx(idx);
    try {
      const res = await apiPost<{ added: number }>("/api/v1/collection/batch", {
        entries: [{ name_en: result.card_name, quantity: 1 }],
      });
      if (res.errors.length > 0) {
        setWebError(res.errors[0].message);
      } else {
        setAddedIdxs((prev) => new Set([...prev, idx]));
      }
    } catch (err: unknown) {
      setWebError(err instanceof Error ? err.message : t("common.unknownError"));
    } finally {
      setAddingIdx(null);
    }
  }, [t]);

  // Add to evaluation handler
  const handleAddToEvaluation = useCallback(async (result: WebSearchResult, idx: number) => {
    setEvalAddingIdx(idx);
    try {
      const res = await createEvaluation({
        card_name: result.card_name,
        liga_url: result.liga_url,
        price_at_add: result.normal_price,
        card_id: result.local_card_id,
      });
      if (res.errors.length > 0) {
        setWebError(res.errors[0].message);
      } else {
        setEvalAddedIdxs((prev) => new Set([...prev, idx]));
      }
    } catch (err: unknown) {
      setWebError(err instanceof Error ? err.message : t("common.unknownError"));
    } finally {
      setEvalAddingIdx(null);
    }
  }, [t]);

  // Handle key press in web search input
  const handleWebKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleWebSearch();
    }
  }, [handleWebSearch]);

  return (
    <div data-testid="page-cards">
      <h2 className="text-2xl font-bold text-white mb-6">{t("cards.title")}</h2>

      {/* Mode toggle - only show Web Search tab when authenticated */}
      {isAuthenticated && (
        <div className="flex gap-1 mb-6 bg-slate-800 rounded-lg p-1 w-fit" data-testid="mode-toggle">
          <button
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              mode === "local"
                ? "bg-cyan-500 text-white"
                : "text-slate-400 hover:text-white"
            }`}
            onClick={() => setMode("local")}
            data-testid="mode-local"
          >
            {t("cards.localSearch")}
          </button>
          <button
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              mode === "web"
                ? "bg-cyan-500 text-white"
                : "text-slate-400 hover:text-white"
            }`}
            onClick={() => setMode("web")}
            data-testid="mode-web"
          >
            {t("cards.searchWeb")}
          </button>
        </div>
      )}

      {/* ===== LOCAL MODE ===== */}
      {mode === "local" && (
        <>
          {/* Search and filters */}
          <div className="space-y-4 mb-6">
            <div className="flex gap-3 items-center">
              <div className="flex-1">
                <SearchBar value={searchTerm} onChange={setSearchTerm} />
              </div>
              <SortSelect
                options={EXPLORE_SORT_OPTIONS}
                value={`${sortBy}-${sortDir}`}
                onChange={handleSortChange}
              />
            </div>

            {setOptions.length > 0 && (
              <FilterChips
                options={setOptions}
                selected={selectedSet}
                onSelect={setSelectedSet}
              />
            )}
          </div>

          {/* Error state */}
          {error && (
            <div className="mb-6">
              <ErrorBanner message={error} variant="inline" />
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div
              className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4"
              data-testid="skeleton-grid"
            >
              {Array.from({ length: 12 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && cards.length === 0 && (
            <EmptyState
              message={
                debouncedSearch || selectedSet
                  ? t("cards.noCardsFiltered")
                  : t("cards.noCardsEmpty")
              }
              action={
                debouncedSearch || selectedSet
                  ? { label: t("common.clearFilters"), onClick: handleClearFilters }
                  : undefined
              }
            />
          )}

          {/* Cards grid */}
          {!loading && cards.length > 0 && (
            <>
              <div
                className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4"
                data-testid="cards-grid"
              >
                {cards.map((card) => (
                  <CardTile key={card.id} card={card} />
                ))}
              </div>

              <div ref={sentinelRef} data-testid="scroll-sentinel" />
              {loadingMore && (
                <div className="flex justify-center mt-4" data-testid="loading-more">
                  <div className="h-6 w-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ===== WEB SEARCH MODE ===== */}
      {mode === "web" && (
        <div data-testid="web-search-section">
          {/* Search input */}
          <div className="flex gap-3 items-center mb-2">
            <input
              type="text"
              className="flex-1 bg-slate-800 text-white border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder={t("cards.webSearchPlaceholder")}
              value={webQuery}
              onChange={(e) => setWebQuery(e.target.value)}
              onKeyDown={handleWebKeyDown}
              data-testid="web-search-input"
            />
            <button
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                cooldown || webLoading || !webQuery.trim()
                  ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                  : "bg-cyan-500 text-white hover:bg-cyan-600"
              }`}
              onClick={handleWebSearch}
              disabled={cooldown || webLoading || !webQuery.trim()}
              data-testid="web-search-btn"
              title={cooldown ? t("cards.searchCooldown") : undefined}
            >
              {webLoading ? t("cards.searching") : t("cards.searchWeb")}
            </button>
          </div>
          <p className="text-xs text-slate-500 mb-6">{t("cards.webSearchCost")}</p>

          {/* Error */}
          {webError && (
            <div className="mb-6">
              <ErrorBanner message={webError} variant="inline" />
            </div>
          )}

          {/* Loading */}
          {webLoading && (
            <div className="flex justify-center py-12" data-testid="web-search-loading">
              <div className="h-8 w-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* No results */}
          {!webLoading && webSearched && webResults.length === 0 && !webError && (
            <EmptyState message={t("cards.noWebResults")} />
          )}

          {/* Results */}
          {!webLoading && webResults.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="web-results-grid">
              {webResults.map((result, idx) => (
                <div
                  key={idx}
                  className="bg-slate-800 border border-slate-700 rounded-lg p-4 flex flex-col gap-3"
                  data-testid="web-result-card"
                >
                  {/* Card image */}
                  {result.image_url && (
                    <img
                      src={result.image_url}
                      alt={result.card_name}
                      className="w-full rounded-md"
                    />
                  )}

                  {/* Card info */}
                  <div>
                    <h3 className="text-white font-semibold text-lg">{result.card_name}</h3>
                    {result.set_name && (
                      <p className="text-slate-400 text-sm">{result.set_name}</p>
                    )}
                  </div>

                  {/* Prices */}
                  <div className="flex gap-4 text-sm">
                    {result.normal_price != null && (
                      <span className="text-green-400">
                        Normal: R$ {result.normal_price.toFixed(2)}
                      </span>
                    )}
                    {result.foil_price != null && (
                      <span className="text-yellow-400">
                        Foil: R$ {result.foil_price.toFixed(2)}
                      </span>
                    )}
                    {result.normal_price == null && result.foil_price == null && (
                      <span className="text-slate-500">{t("common.noPriceData")}</span>
                    )}
                  </div>

                  {/* Liga link */}
                  {result.liga_url && (
                    <a
                      href={result.liga_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 text-xs hover:underline"
                    >
                      LigaMagic
                    </a>
                  )}

                  {/* Action buttons */}
                  <div className="flex gap-2 mt-auto">
                    <button
                      className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        addedIdxs.has(idx)
                          ? "bg-green-700 text-green-200 cursor-default"
                          : addingIdx === idx
                            ? "bg-slate-700 text-slate-400 cursor-wait"
                            : "bg-cyan-600 text-white hover:bg-cyan-700"
                      }`}
                      onClick={() => handleAddToCollection(result, idx)}
                      disabled={addedIdxs.has(idx) || addingIdx === idx}
                      data-testid="add-to-collection-btn"
                    >
                      {addedIdxs.has(idx)
                        ? "Added"
                        : addingIdx === idx
                          ? "..."
                          : t("cards.addToCollection")}
                    </button>
                    <button
                      className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        evalAddedIdxs.has(idx)
                          ? "bg-green-700 text-green-200 cursor-default"
                          : evalAddingIdx === idx
                            ? "bg-slate-700 text-slate-400 cursor-wait"
                            : "bg-amber-600 text-white hover:bg-amber-700"
                      }`}
                      onClick={() => handleAddToEvaluation(result, idx)}
                      disabled={evalAddedIdxs.has(idx) || evalAddingIdx === idx}
                      data-testid="add-to-evaluation-btn"
                    >
                      {evalAddedIdxs.has(idx)
                        ? t("evaluations.addSuccess")
                        : evalAddingIdx === idx
                          ? "..."
                          : t("cards.addToEvaluation")}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
