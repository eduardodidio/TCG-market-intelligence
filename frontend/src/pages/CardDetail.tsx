import { useCallback, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { fetchCardDetail } from "../api/cards";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency, formatDate } from "../utils/format";
import { scryfallImageUrl } from "../utils/scryfall";
import { ErrorBanner } from "../components/ErrorBanner";
import { PriceChart } from "../components/PriceChart";
import { SkeletonChartPanel, SkeletonInfoPanel } from "../components/Skeleton";
import type { CardDetail as CardDetailType } from "../types/api";

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    myp: "MYP Cards",
  };
  return labels[source] ?? source;
}

export function CardDetail() {
  const { id } = useParams<{ id: string }>();
  const cardId = Number(id);

  const { currency } = useCurrency();

  const detailFetcher = useCallback(
    () => fetchCardDetail(cardId, { currency }),
    [cardId, currency],
  );

  const { data: card, loading, error, refetch } = useApi<CardDetailType>(
    detailFetcher,
    [cardId, currency],
  );

  // Set page title
  useEffect(() => {
    if (card) {
      document.title = `${card.name_en} | TCG Market`;
    } else {
      document.title = "Card Detail | TCG Market";
    }
  }, [card]);

  if (loading) {
    return (
      <div data-testid="page-card-detail">
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
    // Check if it's a 404-style error
    const is404 =
      error.toLowerCase().includes("not found") ||
      error.includes("HTTP_404") ||
      error.includes("404");

    if (is404) {
      return (
        <div data-testid="page-card-detail">
          <div data-testid="card-not-found" className="text-center py-12">
            <h2 className="text-2xl font-bold text-white mb-4">Card not found</h2>
            <p className="text-slate-400 mb-6">
              Card not found. It may not have been synced yet.
            </p>
            <Link
              to="/cards"
              className="inline-block rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              Back to Cards
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div data-testid="page-card-detail">
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      </div>
    );
  }

  if (!card) {
    return (
      <div data-testid="page-card-detail">
        <div data-testid="card-not-found" className="text-center py-12">
          <h2 className="text-2xl font-bold text-white mb-4">Card not found</h2>
          <Link
            to="/cards"
            className="inline-block rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            Back to Cards
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="page-card-detail">
      {/* Breadcrumb */}
      <nav data-testid="breadcrumb" className="mb-6 text-sm text-slate-400" aria-label="Breadcrumb">
        <Link to="/cards" className="hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded">
          Cards
        </Link>
        <span className="mx-2" aria-hidden="true">&gt;</span>
        <span className="text-white">{card.name_en}</span>
      </nav>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left panel: Card info */}
        <div data-testid="card-info-panel" className="bg-slate-800 rounded-xl p-6">
          {/* Scryfall card image */}
          {card.set_code && card.collector_number && (
            <div className="mb-6 flex justify-center">
              <img
                src={scryfallImageUrl(card.set_code, card.collector_number, "normal")}
                alt={card.name_en}
                data-testid="card-image"
                className="rounded-xl shadow-lg max-w-[250px] w-full"
                loading="eager"
                onError={(e) => { e.currentTarget.style.display = 'none' }}
              />
            </div>
          )}

          {/* Card name */}
          <h1 className="text-2xl font-bold text-white mb-1">{card.name_en}</h1>
          {card.name_pt && card.name_pt !== card.name_en && (
            <p className="text-sm text-slate-400 mb-4">{card.name_pt}</p>
          )}

          {/* Set and collector number */}
          <div className="flex items-center gap-3 mb-4">
            {card.set_code && (
              <span className="rounded bg-slate-700 px-2 py-1 text-xs font-mono text-slate-300">
                {card.set_code}
              </span>
            )}
            {card.collector_number && (
              <span className="text-sm text-slate-400">
                #{card.collector_number}
              </span>
            )}
          </div>

          {/* Game badge */}
          <span className="inline-block rounded-full bg-cyan-900/50 px-3 py-1 text-xs font-medium text-cyan-300 mb-6">
            {card.game}
          </span>

          {/* Latest price */}
          <div className="mb-6">
            <p className="text-sm text-slate-400 mb-1">Latest Price</p>
            <p data-testid="latest-price" className="text-3xl font-bold text-white">
              {formatCurrency(card.latest_price, currency)}
            </p>
          </div>

          {/* Source links */}
          {card.source_cards.length > 0 && (
            <div className="mb-6">
              <p className="text-sm text-slate-400 mb-2">Sources</p>
              <div className="flex flex-wrap gap-2">
                {card.source_cards.map((sc) => (
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

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-400">First tracked</p>
              <p className="text-white">{formatDate(card.created_at)}</p>
            </div>
            <div>
              <p className="text-slate-400">Last updated</p>
              <p className="text-white">{formatDate(card.updated_at)}</p>
            </div>
          </div>

          {/* External Links */}
          <div className="mt-6" data-testid="external-links">
            <p className="text-sm text-slate-400 mb-2">External Links</p>
            <div className="flex flex-wrap gap-2">
              <a
                href={`https://scryfall.com/search?q=${encodeURIComponent(card.name_en)}${card.set_code ? `+set:${card.set_code}` : ""}`}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="scryfall-link"
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                View on Scryfall
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
              <a
                href={`https://www.ligamagic.com.br/?view=cards/card&card=${encodeURIComponent(card.name_en)}`}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="ligamagic-link"
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                View on LigaMagic
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
            </div>
          </div>
        </div>

        {/* Right panel: Price chart */}
        <div>
          <PriceChart cardId={cardId} currency={currency} />
        </div>
      </div>
    </div>
  );
}
