import { useCallback, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { fetchCollectionEntry } from "../api/collection";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl } from "../utils/scryfall";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { ErrorBanner } from "../components/ErrorBanner";
import { PriceChart } from "../components/PriceChart";
import { SkeletonChartPanel, SkeletonInfoPanel } from "../components/Skeleton";
import type { CollectionCardDetail as CollectionCardDetailType } from "../types/api";

const RARITY_LABELS: Record<string, string> = {
  M: "Mythic",
  R: "Rare",
  U: "Uncommon",
  C: "Common",
};

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    myp: "MYP Cards",
  };
  return labels[source] ?? source;
}

export function CollectionCardDetail() {
  const { id } = useParams<{ id: string }>();
  const entryId = Number(id);

  const { currency } = useCurrency();

  const detailFetcher = useCallback(
    () => fetchCollectionEntry(entryId, { currency }),
    [entryId, currency],
  );

  const { data: entry, loading, error, refetch } = useApi<CollectionCardDetailType>(
    detailFetcher,
    [entryId, currency],
  );

  useEffect(() => {
    if (entry) {
      document.title = `${entry.name_en || entry.name_pt || "Card"} | TCG Market`;
    } else {
      document.title = "Collection Card | TCG Market";
    }
  }, [entry]);

  if (loading) {
    return (
      <div data-testid="page-collection-detail">
        <div className="mb-6">
          <div className="animate-pulse bg-slate-700 rounded h-4 w-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonInfoPanel />
          <SkeletonChartPanel />
        </div>
      </div>
    );
  }

  if (error) {
    const is404 =
      error.toLowerCase().includes("not found") ||
      error.includes("HTTP_404") ||
      error.includes("404");

    if (is404) {
      return (
        <div data-testid="page-collection-detail">
          <div data-testid="entry-not-found" className="text-center py-12">
            <h2 className="text-2xl font-bold text-white mb-4">Collection entry not found</h2>
            <p className="text-slate-400 mb-6">
              This collection entry does not exist.
            </p>
            <Link
              to="/collection"
              className="inline-block rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              Back to Collection
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div data-testid="page-collection-detail">
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      </div>
    );
  }

  if (!entry) {
    return (
      <div data-testid="page-collection-detail">
        <div data-testid="entry-not-found" className="text-center py-12">
          <h2 className="text-2xl font-bold text-white mb-4">Collection entry not found</h2>
          <Link
            to="/collection"
            className="inline-block rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            Back to Collection
          </Link>
        </div>
      </div>
    );
  }

  const displayName = entry.name_en || entry.name_pt || "Unknown Card";
  const imageUrl = entry.image_url || scryfallImageUrl(entry.set_code, entry.collector_number);

  return (
    <div data-testid="page-collection-detail">
      {/* Breadcrumb */}
      <nav data-testid="breadcrumb" className="mb-6 text-sm text-slate-400" aria-label="Breadcrumb">
        <Link to="/collection" className="hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded">
          Collection
        </Link>
        <span className="mx-2" aria-hidden="true">&gt;</span>
        <span className="text-white">{displayName}</span>
      </nav>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left panel: Card info */}
        <div data-testid="card-info-panel" className="bg-slate-800 rounded-xl p-6">
          {/* Card image */}
          <div className="mb-6 flex justify-center">
            <img
              src={imageUrl}
              alt={displayName}
              data-testid="card-image"
              className="rounded-xl shadow-lg max-w-[250px] w-full"
              loading="eager"
              onError={(e) => { e.currentTarget.style.display = "none"; }}
            />
          </div>

          {/* Card name */}
          <h1 className="text-2xl font-bold text-white mb-1">{entry.name_en || "Unknown Card"}</h1>
          {entry.name_pt && entry.name_pt !== entry.name_en && (
            <p className="text-sm text-slate-400 mb-4" data-testid="name-pt">{entry.name_pt}</p>
          )}

          {/* Set and collector number */}
          <div className="flex items-center gap-3 mb-4">
            {entry.set_code && (
              <span className="rounded bg-slate-700 px-2 py-1 text-xs font-mono text-slate-300" data-testid="set-code">
                {entry.set_code}
              </span>
            )}
            {entry.collector_number && (
              <span className="text-sm text-slate-400" data-testid="collector-number">
                #{entry.collector_number}
              </span>
            )}
          </div>

          {/* Collection metadata */}
          <div className="mb-6" data-testid="collection-metadata">
            <p className="text-sm text-slate-400 mb-2">Collection Info</p>
            <div className="flex flex-wrap gap-2">
              {entry.quantity > 1 && (
                <span className="inline-block rounded-full bg-indigo-600 px-3 py-1 text-xs font-bold text-white" data-testid="quantity-badge">
                  x{entry.quantity}
                </span>
              )}
              {entry.quality && (
                <span className="inline-block rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-300" data-testid="quality-badge">
                  {entry.quality}
                </span>
              )}
              {entry.language && (
                <span className="inline-block rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-300" data-testid="language-badge">
                  {entry.language}
                </span>
              )}
              {entry.rarity && (
                <span className="inline-block rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-300" data-testid="rarity-badge">
                  {RARITY_LABELS[entry.rarity] || entry.rarity}
                </span>
              )}
              {entry.extras && (
                <span className="inline-block rounded-full bg-amber-600/90 px-3 py-1 text-xs font-bold text-white" data-testid="extras-badge">
                  {entry.extras}
                </span>
              )}
            </div>
          </div>

          {/* Latest price */}
          <div className="mb-6">
            <p className="text-sm text-slate-400 mb-1">Latest Price</p>
            <p data-testid="latest-price" className="text-3xl font-bold text-white flex items-center gap-2">
              <CurrencyIndicator currency={currency} size={24} />
              {formatCurrency(entry.latest_price, currency)}
            </p>
          </div>

          {/* Linked status */}
          {entry.card_id == null && (
            <div className="mb-6 rounded-lg bg-slate-700/50 p-4" data-testid="unlinked-notice">
              <p className="text-sm text-amber-400">
                Not yet linked to price data
              </p>
              <p className="text-xs text-slate-400 mt-1">
                This card has not been matched to a canonical card in the database.
                Price tracking will begin once it is linked during a sync.
              </p>
            </div>
          )}

          {/* Source links */}
          {entry.source_cards.length > 0 && (
            <div className="mb-6">
              <p className="text-sm text-slate-400 mb-2">Sources</p>
              <div className="flex flex-wrap gap-2">
                {entry.source_cards.map((sc) => (
                  <a
                    key={sc.external_id}
                    href={sc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="source-link"
                    className="inline-flex items-center gap-1 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                  >
                    {sourceLabel(sc.source)}
                    <svg
                      className="h-3 w-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* External Links */}
          <div className="mt-6" data-testid="external-links">
            <p className="text-sm text-slate-400 mb-2">External Links</p>
            <div className="flex flex-wrap gap-2">
              {entry.scryfall_url && (
                <a
                  href={entry.scryfall_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="scryfall-link"
                  className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  View on Scryfall
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
              {entry.ligamagic_url && (
                <a
                  href={entry.ligamagic_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="ligamagic-link"
                  className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  View on LigaMagic
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Right panel: Price chart */}
        <div>
          {entry.card_id != null ? (
            <PriceChart cardId={entry.card_id} currency={currency} />
          ) : (
            <div data-testid="no-price-chart" className="bg-slate-800 rounded-xl p-8 text-center">
              <p className="text-slate-400">
                No price chart available for unlinked cards
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
