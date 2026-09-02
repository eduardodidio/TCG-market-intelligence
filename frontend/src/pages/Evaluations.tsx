import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  fetchEvaluations,
  deleteEvaluation,
  promoteEvaluation,
} from "../api/evaluations";
import type { EvalEntry } from "../api/evaluations";
import { Breadcrumb } from "../components/Breadcrumb";

export function Evaluations() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<EvalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<number | null>(null);

  useEffect(() => {
    document.title = `${t("evaluations.title")} | TCG Market`;
  }, [t]);

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchEvaluations();
      if (res.errors.length > 0) {
        setError(res.errors[0].message);
      } else {
        setEntries(res.data ?? []);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("common.unknownError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const handleRemove = useCallback(
    async (id: number) => {
      setActionInProgress(id);
      try {
        await deleteEvaluation(id);
        setEntries((prev) => prev.filter((e) => e.id !== id));
        setFeedback(t("evaluations.removed"));
        setTimeout(() => setFeedback(null), 3000);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      } finally {
        setActionInProgress(null);
      }
    },
    [t],
  );

  const handlePromote = useCallback(
    async (id: number) => {
      setActionInProgress(id);
      try {
        const res = await promoteEvaluation(id);
        if (res.errors.length > 0) {
          setError(res.errors[0].message);
        } else {
          setEntries((prev) => prev.filter((e) => e.id !== id));
          setFeedback(t("evaluations.promoted"));
          setTimeout(() => setFeedback(null), 3000);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      } finally {
        setActionInProgress(null);
      }
    },
    [t],
  );

  return (
    <div className="max-w-5xl mx-auto p-4">
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("nav.evaluations") },
        ]}
      />
      <h1
        className="text-2xl font-bold text-slate-100 mb-6"
        data-testid="evaluations-title"
      >
        {t("evaluations.title")}
      </h1>

      {feedback && (
        <div
          className="mb-4 px-4 py-2 rounded-md bg-green-800/50 text-green-300 text-sm"
          data-testid="eval-feedback"
        >
          {feedback}
        </div>
      )}

      {error && (
        <div
          className="mb-4 px-4 py-2 rounded-md bg-red-800/50 text-red-300 text-sm"
          data-testid="eval-error"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-slate-400">{t("common.loading")}</div>
      ) : entries.length === 0 ? (
        <div
          className="text-center py-12 text-slate-400"
          data-testid="eval-empty"
        >
          <p className="text-lg mb-2">{t("evaluations.empty")}</p>
          <Link
            to="/cards"
            className="text-cyan-400 hover:underline text-sm"
          >
            {t("nav.exploreCards")}
          </Link>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table
            className="w-full text-sm text-left text-slate-300"
            data-testid="eval-table"
          >
            <thead className="text-xs uppercase text-slate-400 border-b border-slate-700">
              <tr>
                <th className="py-3 px-4">{t("common.noImage")}</th>
                <th className="py-3 px-4">{t("evaluations.title")}</th>
                <th className="py-3 px-4">{t("evaluations.priceAtAdd")}</th>
                <th className="py-3 px-4">{t("evaluations.addedOn")}</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-slate-700/50 hover:bg-slate-800/50"
                  data-testid="eval-row"
                >
                  <td className="py-3 px-4">
                    {entry.image_url ? (
                      <img
                        src={entry.image_url}
                        alt={entry.card_name}
                        className="w-10 h-14 object-cover rounded"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-10 h-14 bg-slate-700 rounded flex items-center justify-center text-xs text-slate-500">
                        ?
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-medium text-slate-200">
                      {entry.card_name}
                    </div>
                    {entry.set_code && (
                      <div className="text-xs text-slate-500">
                        {entry.set_code.toUpperCase()}
                        {entry.collector_number
                          ? ` #${entry.collector_number}`
                          : ""}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {entry.price_at_add != null
                      ? `R$ ${entry.price_at_add.toFixed(2)}`
                      : "--"}
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-400">
                    {entry.created_at
                      ? new Date(entry.created_at).toLocaleDateString()
                      : "--"}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      <button
                        className="px-3 py-1 text-xs rounded bg-cyan-600 text-white hover:bg-cyan-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => handlePromote(entry.id)}
                        disabled={actionInProgress === entry.id}
                        data-testid="promote-btn"
                      >
                        {t("evaluations.promote")}
                      </button>
                      <button
                        className="px-3 py-1 text-xs rounded bg-red-700/50 text-red-300 hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => handleRemove(entry.id)}
                        disabled={actionInProgress === entry.id}
                        data-testid="remove-btn"
                      >
                        {t("evaluations.remove")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
