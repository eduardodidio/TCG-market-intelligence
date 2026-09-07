import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import { deleteAlert, fetchAlerts, fetchNotifications, markAllNotificationsRead } from "../api/alerts";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import type { AlertResponse, AlertNotificationResponse } from "../types/alerts";

type Tab = "active" | "triggered";

export function AlertsPage() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>("active");

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
    </div>
  );
}

function ActiveAlertsTab({
  alerts,
  loading,
  onDelete,
}: {
  alerts: AlertResponse[] | null;
  loading: boolean;
  onDelete: (id: number) => void;
}) {
  const { t } = useTranslation();

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
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="flex items-center justify-between p-4 bg-slate-800 border border-slate-700 rounded-lg"
          data-testid="active-alert-row"
        >
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">
              {alert.card_name ?? t("common.unknownCard")}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              {t(`alerts.direction_${alert.direction}`)}{" "}
              <span className="font-medium text-slate-300">
                R$ {alert.target_price.toFixed(2)}
              </span>
            </p>
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
      ))}
    </div>
  );
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
                <p className="text-sm font-medium text-white truncate">
                  {alert.card_name ?? t("common.unknownCard")}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {t(`alerts.direction_${alert.direction}`)}{" "}
                  <span className="font-medium text-slate-300">
                    R$ {alert.target_price.toFixed(2)}
                  </span>
                </p>
                {notif && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    {notif.old_price !== null ? `R$ ${notif.old_price.toFixed(2)}` : "--"}{" "}
                    → R$ {notif.new_price.toFixed(2)}
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
