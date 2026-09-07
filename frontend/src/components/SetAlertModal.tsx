import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { createAlert, deleteAlert, fetchAlerts } from "../api/alerts";
import type { AlertResponse } from "../types/alerts";

interface SetAlertModalProps {
  cardId: number;
  cardName: string;
  onClose: () => void;
}

export function SetAlertModal({ cardId, cardName, onClose }: SetAlertModalProps) {
  const { t } = useTranslation();
  const [targetPrice, setTargetPrice] = useState("");
  const [direction, setDirection] = useState<"below" | "above">("below");
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [existingAlerts, setExistingAlerts] = useState<AlertResponse[]>([]);
  const [loadingAlerts, setLoadingAlerts] = useState(true);

  const loadExistingAlerts = useCallback(async () => {
    setLoadingAlerts(true);
    try {
      const resp = await fetchAlerts({ status: "active" });
      if (resp.data) {
        setExistingAlerts(
          resp.data.filter((a) => a.card_id === cardId),
        );
      }
    } catch {
      // Ignore
    } finally {
      setLoadingAlerts(false);
    }
  }, [cardId]);

  useEffect(() => {
    loadExistingAlerts();
  }, [loadExistingAlerts]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    const price = parseFloat(targetPrice);
    if (isNaN(price) || price <= 0) {
      setErrorMsg(t("alerts.invalidPrice"));
      return;
    }

    setSubmitting(true);
    try {
      const resp = await createAlert({
        card_id: cardId,
        target_price: price,
        direction,
      });

      if (resp.errors.length > 0) {
        setErrorMsg(resp.errors[0].message);
      } else {
        setSuccessMsg(
          t("alerts.setSuccess", {
            direction: t(`alerts.direction_${direction}`),
            price: price.toFixed(2),
          }),
        );
        setTargetPrice("");
        loadExistingAlerts();
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : t("common.unknownError"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (alertId: number) => {
    try {
      await deleteAlert(alertId);
      setExistingAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch {
      // Ignore
    }
  };

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      data-testid="set-alert-modal-overlay"
    >
      <div
        className="bg-slate-800 border border-slate-600 rounded-lg shadow-xl w-full max-w-md mx-4"
        data-testid="set-alert-modal"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-600">
          <h2 className="text-lg font-semibold text-white">
            {t("alerts.setAlertTitle")}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
            aria-label={t("common.cancel")}
            data-testid="close-modal"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4">
          <p className="text-sm text-slate-300 mb-4">
            {t("alerts.setAlertDescription", { cardName })}
          </p>

          <form onSubmit={handleSubmit} data-testid="set-alert-form">
            {/* Direction toggle */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                {t("alerts.directionLabel")}
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setDirection("below")}
                  className={`flex-1 px-3 py-2 text-sm rounded-md transition-colors ${
                    direction === "below"
                      ? "bg-green-600 text-white"
                      : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                  }`}
                  data-testid="direction-below"
                >
                  {t("alerts.direction_below")}
                </button>
                <button
                  type="button"
                  onClick={() => setDirection("above")}
                  className={`flex-1 px-3 py-2 text-sm rounded-md transition-colors ${
                    direction === "above"
                      ? "bg-red-600 text-white"
                      : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                  }`}
                  data-testid="direction-above"
                >
                  {t("alerts.direction_above")}
                </button>
              </div>
            </div>

            {/* Price input */}
            <div className="mb-4">
              <label
                htmlFor="target-price"
                className="block text-sm font-medium text-slate-300 mb-2"
              >
                {t("alerts.targetPriceLabel")}
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                  R$
                </span>
                <input
                  id="target-price"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={targetPrice}
                  onChange={(e) => setTargetPrice(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="0.00"
                  data-testid="target-price-input"
                  required
                />
              </div>
            </div>

            {/* Error/success messages */}
            {errorMsg && (
              <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-md text-sm text-red-300" data-testid="alert-error">
                {errorMsg}
              </div>
            )}
            {successMsg && (
              <div className="mb-4 p-3 bg-green-900/30 border border-green-700 rounded-md text-sm text-green-300" data-testid="alert-success">
                {successMsg}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white text-sm font-medium rounded-md transition-colors"
              data-testid="submit-alert"
            >
              {submitting ? t("common.pleaseWait") : t("alerts.setAlertButton")}
            </button>
          </form>

          {/* Existing alerts for this card */}
          {!loadingAlerts && existingAlerts.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-slate-300 mb-2">
                {t("alerts.existingAlerts")}
              </h3>
              <div className="space-y-2">
                {existingAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between px-3 py-2 bg-slate-700 rounded-md"
                    data-testid="existing-alert-item"
                  >
                    <span className="text-sm text-slate-300">
                      {t(`alerts.direction_${alert.direction}`)}{" "}
                      R$ {alert.target_price.toFixed(2)}
                    </span>
                    <button
                      onClick={() => handleDelete(alert.id)}
                      className="text-xs text-red-400 hover:text-red-300 transition-colors"
                      data-testid="delete-existing-alert"
                    >
                      {t("common.delete")}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
