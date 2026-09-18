import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import { deleteAlert, fetchAlerts, fetchNotifications, markAllNotificationsRead, updateAlert } from "../api/alerts";
import { Breadcrumb } from "../components/Breadcrumb";
import { CardSearchAlertModal } from "../components/CardSearchAlertModal";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import type { AlertResponse, AlertNotificationResponse } from "../types/alerts";

type Tab = "active" | "triggered";

export function AlertsPage() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>("active");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const activeAlertsFetcher = useCallback(
    () => fetchAlerts({ status: "active", limit: "100" }),
    [],
  );
  const triggeredAlertsFetcher = useCallback(
    () => fetchAlerts({ status: "triggered", limit: "100" }),
    [],
  );
  const notificationsFetcher = useCallback(
    () => fetchNotifications({ limit: "100" }),
    [],
  );

  const {
    data: activeAlerts,
    loading: activeLoading,
    refetch: refetchActive,
  } = useApi<AlertResponse[]>(activeAlertsFetcher, []);

  const {
    data: triggeredAlerts,
    loading: triggeredLoading,
    refetch: refetchTriggered,
  } = useApi<AlertResponse[]>(triggeredAlertsFetcher, []);

  const {
    data: notificationsData,
    refetch: refetchNotifications,
  } = useApi(notificationsFetcher, []);

  const handleDeleteAlert = async (alertId: number) => {
    try {
      await deleteAlert(alertId);
      if (activeTab === "active") {
        refetchActive();
      } else {
        refetchTriggered();
      }
    } catch {
      // Ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      refetchNotifications();
    } catch {
      // Ignore
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12 text-slate-400">
        {t("alerts.loginRequired")}
      </div>
    );
  }

  const breadcrumbs = [
    { label: t("nav.dashboard"), to: "/" },
    { label: t("alerts.title") },
  ];

  const tabs: { key: Tab; labelKey: string }[] = [
    { key: "active", labelKey: "alerts.tabActive" },
    { key: "triggered", labelKey: "alerts.tabTriggered" },
  ];

  return (
    <div>
      <Breadcrumb items={breadcrumbs} />
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{t("alerts.title")}</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-md transition-colors"
          data-testid="create-alert-button"
        >
          {t("alerts.createAlert")}
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === tab.key
                ? "border-indigo-500 text-white"
                : "border-transparent text-slate-400 hover:text-white"
            }`}
            data-testid={`tab-${tab.key}`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {/* Active tab */}
      {activeTab === "active" && (
        <ActiveAlertsTab
          alerts={activeAlerts}
          loading={activeLoading}
          onDelete={handleDeleteAlert}
          onUpdate={refetchActive}
        />
      )}

      {/* Triggered tab */}
      {activeTab === "triggered" && (
        <TriggeredAlertsTab
          alerts={triggeredAlerts}
          notifications={notificationsData?.notifications ?? []}
          loading={triggeredLoading}
          onDelete={handleDeleteAlert}
          onMarkAllRead={handleMarkAllRead}
        />
      )}

      {/* Create Alert Modal */}
      {showCreateModal && (
        <CardSearchAlertModal
          onClose={() => setShowCreateModal(false)}
          onAlertCreated={() => { setShowCreateModal(false); refetchActive(); }}
        />
      )}
    </div>
  );
}

function ActiveAlertsTab({
  alerts,
  loading,
  onDelete,
  onUpdate,
}: {
  alerts: AlertResponse[] | null;
  loading: boolean;
  onDelete: (id: number) => void;
  onUpdate: () => void;
}) {
  const { t } = useTranslation();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);

  const handleStartEdit = (alert: AlertResponse) => {
    setEditingId(alert.id);
    setEditValue(alert.target_price.toFixed(2));
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditValue("");
  };

  const handleSaveEdit = async (alertId: number) => {
    const price = parseFloat(editValue);
    if (isNaN(price) || price <= 0) return;

    setSaving(true);
    try {
      const resp = await updateAlert(alertId, { target_price: price });
      if (resp.errors.length === 0) {
        onUpdate();
      }
    } catch {
      // Ignore
    } finally {
      setSaving(false);
      setEditingId(null);
    }
  };

  const handleEditKeyDown = (e: React.KeyboardEvent, alertId: number) => {
    if (e.key === "Enter") {
      handleSaveEdit(alertId);
    } else if (e.key === "Escape") {
      handleCancelEdit();
    }
  };

  if (loading) return <LoadingSpinner message={t("common.loading")} />;

  if (!alerts || alerts.length === 0) {
    return (
      <EmptyState
        title={t("alerts.emptyActiveTitle")}
        description={t("alerts.emptyActiveDescription")}
      />
    );
  }

  return (
    <div className="space-y-2" data-testid="active-alerts-list">
      {alerts.map((alert) => {
        const isEditing = editingId === alert.id;
        const priceColor = getPriceColor(alert);

        return (
          <div
            key={alert.id}
            className="flex items-center justify-between p-4 bg-slate-800 border border-slate-700 rounded-lg"
            data-testid="active-alert-row"
          >
            <div className="flex-1 min-w-0">
              <Link
                to={`/cards/${alert.card_id}`}
                className="text-sm font-medium text-white hover:text-indigo-400 truncate transition-colors block"
                data-testid="alert-card-link"
              >
                {alert.card_name ?? t("common.unknownCard")}
              </Link>
              <div className="text-xs text-slate-400 mt-1">
                {isEditing ? (
                  <span className="inline-flex items-center gap-1">
                    {t(`alerts.direction_${alert.direction}`)}{" "}
                    <span className="text-slate-300">R$</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => handleEditKeyDown(e, alert.id)}
                      onBlur={() => handleSaveEdit(alert.id)}
                      className="w-20 px-1 py-0.5 bg-slate-700 border border-slate-500 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      data-testid="inline-edit-input"
                      autoFocus
                      disabled={saving}
                    />
                    <button
                      onClick={() => handleSaveEdit(alert.id)}
                      className="text-green-400 hover:text-green-300"
                      data-testid="inline-edit-save"
                      disabled={saving}
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="text-red-400 hover:text-red-300"
                      data-testid="inline-edit-cancel"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ) : (
                  <span>
                    {t(`alerts.direction_${alert.direction}`)}{" "}
                    <span className="font-medium text-slate-300">
                      R$ {alert.target_price.toFixed(2)}
                    </span>
                    <button
                      onClick={() => handleStartEdit(alert)}
                      className="ml-1.5 text-slate-500 hover:text-slate-300 transition-colors"
                      title={t("alerts.editTargetPrice")}
                      data-testid="inline-edit-button"
                    >
                      <svg className="h-3 w-3 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  </span>
                )}
              </div>
              {alert.current_price != null && (
                <p className={`text-xs mt-0.5 ${priceColor}`} data-testid="alert-current-price">
                  {t("alerts.currentPrice", { price: alert.current_price.toFixed(2) })}
                  {" "}
                  ({getPercentLabel(alert)})
                </p>
              )}
              <p className="text-xs text-slate-500 mt-0.5">
                {t("alerts.createdAt")}: {new Date(alert.created_at).toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={() => onDelete(alert.id)}
              className="ml-4 px-3 py-1 text-xs text-red-400 border border-red-700 rounded-md hover:bg-red-900/30 transition-colors"
              data-testid="delete-alert-button"
            >
              {t("common.delete")}
            </button>
          </div>
        );
      })}
    </div>
  );
}

function getPriceColor(alert: AlertResponse): string {
  if (alert.current_price == null) return "text-slate-400";
  const diff = alert.current_price - alert.target_price;
  const pct = Math.abs(diff / alert.target_price);

  if (alert.direction === "below") {
    // Waiting for price to drop below target
    if (alert.current_price <= alert.target_price) return "text-red-400";
    if (pct <= 0.1) return "text-yellow-400";
    return "text-green-400";
  } else {
    // Waiting for price to rise above target
    if (alert.current_price >= alert.target_price) return "text-red-400";
    if (pct <= 0.1) return "text-yellow-400";
    return "text-green-400";
  }
}

function getPercentLabel(alert: AlertResponse): string {
  if (alert.current_price == null) return "";
  const diff = alert.current_price - alert.target_price;
  const pct = Math.abs((diff / alert.target_price) * 100).toFixed(0);
  if (diff > 0) return `${pct}% above`;
  if (diff < 0) return `${pct}% below`;
  return "at target";
}

function TriggeredAlertsTab({
  alerts,
  notifications,
  loading,
  onDelete,
  onMarkAllRead,
}: {
  alerts: AlertResponse[] | null;
  notifications: AlertNotificationResponse[];
  loading: boolean;
  onDelete: (id: number) => void;
  onMarkAllRead: () => void;
}) {
  const { t } = useTranslation();

  if (loading) return <LoadingSpinner message={t("common.loading")} />;

  if (!alerts || alerts.length === 0) {
    return (
      <EmptyState
        title={t("alerts.emptyTriggeredTitle")}
        description={t("alerts.emptyTriggeredDescription")}
      />
    );
  }

  // Build a map from alert_id -> notification for price details
  const notifByAlert = new Map<number, AlertNotificationResponse>();
  for (const n of notifications) {
    if (!notifByAlert.has(n.alert_id)) {
      notifByAlert.set(n.alert_id, n);
    }
  }

  const hasUnread = notifications.some((n) => !n.is_read);

  return (
    <div>
      {hasUnread && (
        <div className="flex justify-end mb-3">
          <button
            onClick={onMarkAllRead}
            className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            data-testid="mark-all-read-page"
          >
            {t("alerts.markAllRead")}
          </button>
        </div>
      )}
      <div className="space-y-2" data-testid="triggered-alerts-list">
        {alerts.map((alert) => {
          const notif = notifByAlert.get(alert.id);
          return (
            <div
              key={alert.id}
              className="flex items-center justify-between p-4 bg-slate-800 border border-slate-700 rounded-lg"
              data-testid="triggered-alert-row"
            >
              <div className="flex-1 min-w-0">
                <Link
                  to={`/cards/${alert.card_id}`}
                  className="text-sm font-medium text-white hover:text-indigo-400 truncate transition-colors block"
                  data-testid="alert-card-link"
                >
                  {alert.card_name ?? t("common.unknownCard")}
                </Link>
                <p className="text-xs text-slate-400 mt-1">
                  {t(`alerts.direction_${alert.direction}`)}{" "}
                  <span className="font-medium text-slate-300">
                    R$ {alert.target_price.toFixed(2)}
                  </span>
                </p>
                {notif && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    {notif.old_price !== null ? `R$ ${notif.old_price.toFixed(2)}` : "--"}{" "}
                    &rarr; R$ {notif.new_price.toFixed(2)}
                  </p>
                )}
                {alert.triggered_at && (
                  <p className="text-xs text-slate-500 mt-0.5">
                    {t("alerts.triggeredAt")}: {new Date(alert.triggered_at).toLocaleDateString()}
                  </p>
                )}
              </div>
              <button
                onClick={() => onDelete(alert.id)}
                className="ml-4 px-3 py-1 text-xs text-slate-400 border border-slate-600 rounded-md hover:bg-slate-700 transition-colors"
                data-testid="dismiss-alert-button"
              >
                {t("alerts.dismiss")}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
