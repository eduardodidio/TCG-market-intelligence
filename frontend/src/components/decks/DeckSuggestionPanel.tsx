import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import {
  deleteDeckSuggestion,
  getDeckSuggestion,
  listDeckSuggestions,
} from "../../api/deckSuggestions";
import type { DeckSuggestion } from "../../types/deckSuggestions";
import { ErrorBanner } from "../ErrorBanner";
import { SuggestionRequestForm } from "./SuggestionRequestForm";
import { SuggestionRequestList } from "./SuggestionRequestList";
import { SuggestionResultView } from "./SuggestionResultView";

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/**
 * Suggestion mode of `/decks/build` (F172): request form on top, the
 * user's requests on the left and the selected request's result on the
 * right (single column below `md`).
 */
export function DeckSuggestionPanel() {
  const { t } = useTranslation();

  const [items, setItems] = useState<DeckSuggestion[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<DeckSuggestion | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Guards against out-of-order responses: only the latest request wins.
  const listRequestId = useRef(0);
  const detailRequestId = useRef(0);

  const loadList = useCallback(async () => {
    const reqId = ++listRequestId.current;
    setListLoading(true);
    setListError(null);
    try {
      const resp = await listDeckSuggestions();
      if (reqId !== listRequestId.current) return;
      if (resp.errors && resp.errors.length > 0) {
        setListError(resp.errors[0].message);
      } else {
        setItems(resp.data ?? []);
      }
    } catch (err) {
      if (reqId !== listRequestId.current) return;
      setListError(errorMessage(err));
    } finally {
      if (reqId === listRequestId.current) setListLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: number) => {
    const reqId = ++detailRequestId.current;
    setDetailLoading(true);
    setDetailError(null);
    try {
      const resp = await getDeckSuggestion(id);
      if (reqId !== detailRequestId.current) return;
      if (resp.errors && resp.errors.length > 0) {
        setDetailError(resp.errors[0].message);
      } else if (resp.data) {
        const fresh = resp.data;
        setDetail(fresh);
        // Keep the list row's status/summary in sync with the detail.
        setItems((prev) =>
          prev.map((s) => (s.id === fresh.id ? { ...s, ...fresh } : s)),
        );
      }
    } catch (err) {
      if (reqId !== detailRequestId.current) return;
      setDetailError(errorMessage(err));
    } finally {
      if (reqId === detailRequestId.current) setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const handleSelect = useCallback(
    (id: number) => {
      setSelectedId(id);
      setDetail(null);
      void loadDetail(id);
    },
    [loadDetail],
  );

  const handleCreated = useCallback((s: DeckSuggestion) => {
    setItems((prev) => [s, ...prev.filter((x) => x.id !== s.id)]);
    // A fresh request is pending and has no result — no need to refetch.
    detailRequestId.current++;
    setSelectedId(s.id);
    setDetail(s);
    setDetailLoading(false);
    setDetailError(null);
  }, []);

  const handleDelete = useCallback(
    async (id: number) => {
      setListError(null);
      try {
        await deleteDeckSuggestion(id);
      } catch (err) {
        setListError(errorMessage(err));
        return;
      }
      setItems((prev) => prev.filter((s) => s.id !== id));
      if (id === selectedId) {
        detailRequestId.current++;
        setSelectedId(null);
        setDetail(null);
        setDetailLoading(false);
        setDetailError(null);
      }
    },
    [selectedId],
  );

  const handleRefresh = useCallback(() => {
    void loadList();
    if (selectedId !== null) void loadDetail(selectedId);
  }, [loadList, loadDetail, selectedId]);

  const handleSaved = useCallback((deckId: number) => {
    const markSaved = (s: DeckSuggestion) => ({ ...s, saved_deck_id: deckId });
    setDetail((prev) => (prev ? markSaved(prev) : prev));
    setItems((prev) =>
      prev.map((s) => (s.id === selectedId ? markSaved(s) : s)),
    );
  }, [selectedId]);

  let resultArea: ReactNode;
  if (selectedId === null) {
    resultArea = (
      <p
        className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400"
        data-testid="suggestion-panel-placeholder"
      >
        {t("deckSuggest.panel.selectPrompt", {
          defaultValue: "Selecione um pedido para ver a sugestão.",
        })}
      </p>
    );
  } else if (detailError) {
    resultArea = (
      <ErrorBanner
        message={detailError}
        onRetry={() => void loadDetail(selectedId)}
      />
    );
  } else if (detailLoading || !detail) {
    resultArea = (
      <div
        className="h-32 animate-pulse rounded-lg bg-slate-800"
        data-testid="suggestion-detail-loading"
      />
    );
  } else {
    resultArea = (
      <SuggestionResultView
        key={detail.id}
        suggestion={detail}
        onSaved={handleSaved}
      />
    );
  }

  return (
    <div data-testid="deck-suggestion-panel" className="space-y-6">
      <SuggestionRequestForm onCreated={handleCreated} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[320px_1fr]">
        <div className="space-y-3 min-w-0">
          {listError && (
            <ErrorBanner message={listError} onRetry={() => void loadList()} />
          )}
          <SuggestionRequestList
            items={items}
            selectedId={selectedId}
            loading={listLoading}
            onSelect={handleSelect}
            onRefresh={handleRefresh}
            onDelete={(id) => void handleDelete(id)}
          />
        </div>
        <div className="min-w-0" data-testid="suggestion-result-area">
          {resultArea}
        </div>
      </div>
    </div>
  );
}
