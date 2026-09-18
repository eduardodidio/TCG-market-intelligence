import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchCards } from "../api/cards";
import { SetAlertModal } from "./SetAlertModal";
import type { CardSummary } from "../types/api";

interface CardSearchAlertModalProps {
  onClose: () => void;
  onAlertCreated: () => void;
}

export function CardSearchAlertModal({ onClose, onAlertCreated }: CardSearchAlertModalProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<"search" | "configure">("search");
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<CardSummary[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedCard, setSelectedCard] = useState<{ id: number; name: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Focus input on mount
  useEffect(() => {
    if (step === "search") {
      inputRef.current?.focus();
    }
  }, [step]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const doSearch = useCallback(async (term: string) => {
    if (term.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const resp = await fetchCards({ q: term.trim(), limit: "20" });
      setSearchResults(resp.data ?? []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(value), 300);
  };

  const handleSelectCard = (card: CardSummary) => {
    setSelectedCard({ id: card.id, name: card.name_en });
    setStep("configure");
  };

  const handleBack = () => {
    setSelectedCard(null);
    setStep("search");
  };

  if (step === "configure" && selectedCard) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-hidden"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
        data-testid="card-search-alert-modal-overlay"
      >
        <div className="bg-slate-800 border border-slate-600 rounded-lg shadow-xl w-full max-w-md mx-4 min-w-0">
          <div className="px-6 py-3 border-b border-slate-600">
            <button
              onClick={handleBack}
              className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
              data-testid="back-to-search"
            >
              &larr; {t("alerts.backToSearch")}
            </button>
          </div>
          <SetAlertModal
            cardId={selectedCard.id}
            cardName={selectedCard.name}
            onClose={() => {
              onAlertCreated();
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-hidden"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      data-testid="card-search-alert-modal-overlay"
    >
      <div
        className="bg-slate-800 border border-slate-600 rounded-lg shadow-xl w-full max-w-md mx-4 min-w-0"
        data-testid="card-search-alert-modal"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-600">
          <h2 className="text-lg font-semibold text-white">
            {t("alerts.createAlert")}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
            aria-label={t("common.cancel")}
            data-testid="close-search-modal"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="px-6 py-4">
          <p className="text-sm text-slate-400 mb-3">{t("alerts.selectCard")}</p>
          <div className="relative mb-4">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={searchTerm}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder={t("alerts.searchCard")}
              className="w-full pl-10 pr-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              data-testid="card-search-input"
            />
          </div>

          {/* Results */}
          <div className="max-h-64 overflow-y-auto">
            {searching && (
              <div className="text-center py-4 text-slate-400 text-sm" data-testid="search-loading">
                {t("common.loading")}
              </div>
            )}
            {!searching && searchTerm.trim().length >= 2 && searchResults.length === 0 && (
              <div className="text-center py-4 text-slate-400 text-sm" data-testid="search-no-results">
                {t("alerts.noResults")}
              </div>
            )}
            {!searching && searchResults.map((card) => (
              <button
                key={card.id}
                onClick={() => handleSelectCard(card)}
                className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-slate-700 rounded-md transition-colors"
                data-testid="search-result-item"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white truncate">{card.name_en}</p>
                  {card.set_code && (
                    <p className="text-xs text-slate-400">{card.set_code.toUpperCase()}</p>
                  )}
                </div>
                {card.latest_price != null && (
                  <span className="text-sm text-slate-300 ml-2 shrink-0">
                    R$ {card.latest_price.toFixed(2)}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
