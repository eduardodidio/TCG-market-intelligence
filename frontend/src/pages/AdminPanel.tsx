import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  fetchAdminUsers,
  fetchAdminDashboard,
  adjustUserCredits,
  createUser,
  deleteUser,
} from "../api/admin";
import type { AdminUser, AdminDashboard, CreateUserResult } from "../api/admin";
import type { ApiResponse } from "../types/api";
import { useAuth } from "../hooks/useAuth";
import { AccordionSection } from "../components/AccordionSection";
import { AdminLigaSection } from "../components/admin/AdminLigaSection";
import { AdminSchedulesSection } from "../components/admin/AdminSchedulesSection";
import { AdminScansSection } from "../components/admin/AdminScansSection";
import { AdminErrorsSection } from "../components/admin/AdminErrorsSection";

const LIMIT = 50;

function KpiCard({
  label,
  value,
  accent = "cyan",
}: {
  label: string;
  value: number | string;
  accent?: string;
}) {
  const colorMap: Record<string, string> = {
    cyan: "text-cyan-400",
    green: "text-green-400",
    amber: "text-amber-400",
    red: "text-red-400",
  };
  return (
    <div
      className="bg-slate-800 rounded-lg p-4 border border-slate-700"
      data-testid={`kpi-${label.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
    >
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colorMap[accent] || "text-white"}`}>
        {value}
      </p>
    </div>
  );
}

function CreateUserForm({ onCreated }: { onCreated: () => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CreateUserResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setSubmitting(true);
    setError(null);
    const resp = await createUser(email, displayName || undefined);
    setSubmitting(false);
    if (resp.errors.length > 0) {
      setError(resp.errors.map((e) => e.message).join("; "));
    } else if (resp.data) {
      setResult(resp.data);
      setEmail("");
      setDisplayName("");
      onCreated();
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="mb-4 px-4 py-2 text-sm bg-green-700 hover:bg-green-600 text-white rounded-lg"
        data-testid="create-user-toggle"
      >
        {t("admin.createUserBtn")}
      </button>
    );
  }

  return (
    <div
      className="mb-4 bg-slate-800 rounded-lg border border-slate-700 p-4"
      data-testid="create-user-form"
    >
      <h3 className="text-white font-medium mb-3">{t("admin.createUser")}</h3>

      {result && (
        <div
          className="mb-3 p-3 rounded-md bg-green-900/30 border border-green-700/50"
          data-testid="create-user-result"
        >
          <p className="text-green-400 text-sm font-medium mb-1">
            {t("admin.userCreated")}
          </p>
          <p className="text-white text-sm">
            {t("admin.temporaryPassword")}:{" "}
            <code
              className="bg-slate-900 px-2 py-0.5 rounded font-mono text-cyan-300 select-all"
              data-testid="temp-password"
            >
              {result.temporary_password}
            </code>
          </p>
          <p className="text-amber-400 text-xs mt-1">
            {t("admin.passwordWarning")}
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div className="flex gap-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t("admin.emailLabel")}
            required
            className="flex-1 px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="create-email-input"
          />
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={t("admin.displayNameLabel")}
            className="flex-1 px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="create-displayname-input"
          />
        </div>
        {error && (
          <p
            className="text-xs text-red-400"
            data-testid="create-user-error"
          >
            {error}
          </p>
        )}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting || !email}
            className="px-4 py-2 text-sm bg-green-700 hover:bg-green-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded"
            data-testid="create-user-submit"
          >
            {submitting ? t("common.pleaseWait") : t("admin.createUserBtn")}
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              setResult(null);
              setError(null);
            }}
            className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded"
          >
            {t("common.cancel")}
          </button>
        </div>
      </form>
    </div>
  );
}

function AdjustCreditsRow({
  user,
  currentUserId,
  onApplied,
  onDeleted,
}: {
  user: AdminUser;
  currentUserId: number;
  onApplied: () => void;
  onDeleted: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const isSelf = user.id === currentUserId;

  const handleDelete = async () => {
    setDeleting(true);
    const resp = await deleteUser(user.id);
    setDeleting(false);
    if (resp.errors.length > 0) {
      setError(resp.errors.map((e) => e.message).join("; "));
    } else {
      setConfirmDelete(false);
      onDeleted();
    }
  };

  const handleApply = async () => {
    const parsed = parseInt(amount, 10);
    if (isNaN(parsed) || parsed === 0) return;
    setSubmitting(true);
    setError(null);
    const resp: ApiResponse<unknown> = await adjustUserCredits(
      user.id,
      parsed,
      reason || undefined,
    );
    setSubmitting(false);
    if (resp.errors.length > 0) {
      setError(resp.errors.map((e) => e.message).join("; "));
    } else {
      setOpen(false);
      setAmount("");
      setReason("");
      onApplied();
    }
  };

  return (
    <tr
      key={user.id}
      className="border-t border-slate-700 hover:bg-slate-700/50"
      data-testid={`user-row-${user.id}`}
    >
      <td className="px-4 py-2 text-white">
        {user.display_name || user.email}
      </td>
      <td className="px-4 py-2 text-slate-400">{user.email}</td>
      <td className="px-4 py-2">
        {user.is_admin ? (
          <span className="text-xs bg-cyan-900 text-cyan-300 px-2 py-0.5 rounded" data-testid={`admin-badge-${user.id}`}>
            {t("admin.adminBadge")}
          </span>
        ) : null}
      </td>
      <td className="px-4 py-2 text-white font-mono" data-testid={`balance-${user.id}`}>
        {user.credit_balance}
      </td>
      <td className="px-4 py-2">
        {!open ? (
          <button
            onClick={() => setOpen(true)}
            className="px-3 py-1 text-sm bg-cyan-700 hover:bg-cyan-600 text-white rounded"
            data-testid={`adjust-btn-${user.id}`}
          >
            {t("admin.adjustCredits")}
          </button>
        ) : (
          <div className="flex flex-col gap-2" data-testid={`adjust-form-${user.id}`}>
            <div className="flex gap-2 items-center">
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder={t("admin.amountPlaceholder")}
                className="w-24 px-2 py-1 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
                data-testid={`amount-input-${user.id}`}
              />
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder={t("admin.reasonPlaceholder")}
                className="w-40 px-2 py-1 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
                data-testid={`reason-input-${user.id}`}
              />
              <button
                onClick={handleApply}
                disabled={submitting || !amount || parseInt(amount, 10) === 0}
                className="px-3 py-1 text-sm bg-green-700 hover:bg-green-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded"
                data-testid={`apply-btn-${user.id}`}
              >
                {submitting ? t("common.pleaseWait") : t("admin.apply")}
              </button>
              <button
                onClick={() => {
                  setOpen(false);
                  setAmount("");
                  setReason("");
                  setError(null);
                }}
                className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded"
              >
                {t("common.cancel")}
              </button>
            </div>
            {error && (
              <p className="text-xs text-red-400" data-testid={`adjust-error-${user.id}`}>
                {error}
              </p>
            )}
          </div>
        )}
      </td>
      <td className="px-4 py-2">
        {!isSelf && user.is_active && (
          <>
            {!confirmDelete ? (
              <button
                onClick={() => setConfirmDelete(true)}
                className="px-3 py-1 text-sm bg-red-800 hover:bg-red-700 text-white rounded"
                data-testid={`delete-btn-${user.id}`}
              >
                {t("admin.deleteUser")}
              </button>
            ) : (
              <div className="flex gap-1 items-center" data-testid={`delete-confirm-${user.id}`}>
                <span className="text-xs text-red-400 mr-1">{t("admin.deleteConfirm")}</span>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-2 py-1 text-xs bg-red-700 hover:bg-red-600 text-white rounded"
                  data-testid={`delete-yes-${user.id}`}
                >
                  {deleting ? "..." : t("common.yes")}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded"
                  data-testid={`delete-no-${user.id}`}
                >
                  {t("common.no")}
                </button>
              </div>
            )}
          </>
        )}
        {!user.is_active && (
          <span className="text-xs text-red-400" data-testid={`inactive-badge-${user.id}`}>
            {t("admin.inactive")}
          </span>
        )}
      </td>
    </tr>
  );
}

export function AdminPanel() {
  const { t } = useTranslation();
  const { user: currentUser } = useAuth();
  const [openSection, setOpenSection] = useState<string | null>("users");

  const toggleSection = (section: string) => {
    setOpenSection((prev) => (prev === section ? null : section));
  };

  // Users state
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersOffset, setUsersOffset] = useState(0);
  const [usersLoaded, setUsersLoaded] = useState(false);

  // Dashboard state
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [dashboardLoaded, setDashboardLoaded] = useState(false);

  useEffect(() => {
    document.title = `${t("admin.title")} | TCG Market`;
  }, [t]);

  const loadUsers = useCallback(async (offset: number) => {
    setUsersLoading(true);
    setUsersError(null);
    const resp = await fetchAdminUsers(LIMIT, offset);
    if (resp.errors.length > 0) {
      setUsersError(resp.errors.map((e) => e.message).join("; "));
      setUsers([]);
    } else if (resp.data) {
      setUsers(resp.data);
      setUsersTotal(resp.meta.total ?? resp.data.length);
    }
    setUsersLoading(false);
    setUsersLoaded(true);
  }, []);

  const loadDashboard = useCallback(async () => {
    setDashboardLoading(true);
    setDashboardError(null);
    const resp = await fetchAdminDashboard();
    if (resp.errors.length > 0) {
      setDashboardError(resp.errors.map((e) => e.message).join("; "));
      setDashboard(null);
    } else {
      setDashboard(resp.data);
    }
    setDashboardLoading(false);
    setDashboardLoaded(true);
  }, []);

  // Load users when section is opened (or offset changes)
  useEffect(() => {
    if (openSection === "users") {
      loadUsers(usersOffset);
    }
  }, [openSection, usersOffset, loadUsers]);

  // Load dashboard when section is opened (lazy)
  useEffect(() => {
    if (openSection === "dashboard" && !dashboardLoaded) {
      loadDashboard();
    }
  }, [openSection, dashboardLoaded, loadDashboard]);

  const hasNextPage = usersOffset + LIMIT < usersTotal;
  const hasPrevPage = usersOffset > 0;

  return (
    <div data-testid="page-admin-panel">
      <h1 className="text-2xl font-bold text-white mb-6">
        {t("admin.title")}
      </h1>

      {/* Users Section */}
      <AccordionSection
        title={t("admin.section.users")}
        isOpen={openSection === "users"}
        onToggle={() => toggleSection("users")}
      >
        <div data-testid="users-section">
          <CreateUserForm onCreated={() => loadUsers(usersOffset)} />
          <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
            {usersLoading ? (
              <p className="p-4 text-slate-400" data-testid="users-loading">
                {t("common.loading")}
              </p>
            ) : usersError ? (
              <p className="p-4 text-red-400" data-testid="users-error">
                {usersError}
              </p>
            ) : users.length === 0 ? (
              <p className="p-4 text-slate-400" data-testid="users-empty">
                {t("admin.noUsers")}
              </p>
            ) : (
              <>
                <table
                  className="w-full text-sm text-left"
                  data-testid="users-table"
                >
                  <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                    <tr>
                      <th className="px-4 py-2">{t("admin.colName")}</th>
                      <th className="px-4 py-2">{t("admin.colEmail")}</th>
                      <th className="px-4 py-2">{t("admin.colRole")}</th>
                      <th className="px-4 py-2">{t("admin.colBalance")}</th>
                      <th className="px-4 py-2">{t("admin.colActions")}</th>
                      <th className="px-4 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <AdjustCreditsRow
                        key={user.id}
                        user={user}
                        currentUserId={currentUser?.id ?? 0}
                        onApplied={() => loadUsers(usersOffset)}
                        onDeleted={() => loadUsers(usersOffset)}
                      />
                    ))}
                  </tbody>
                </table>

                {/* Pagination */}
                <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
                  <span className="text-xs text-slate-400" data-testid="users-pagination-info">
                    {usersOffset + 1}--
                    {Math.min(usersOffset + LIMIT, usersTotal)} {t("common.of")}{" "}
                    {usersTotal}
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={!hasPrevPage}
                      onClick={() =>
                        setUsersOffset(Math.max(0, usersOffset - LIMIT))
                      }
                      className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                      data-testid="users-prev"
                    >
                      {t("common.prev")}
                    </button>
                    <button
                      disabled={!hasNextPage}
                      onClick={() => setUsersOffset(usersOffset + LIMIT)}
                      className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                      data-testid="users-next"
                    >
                      {t("common.next")}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </AccordionSection>

      {/* Dashboard Section */}
      <AccordionSection
        title={t("admin.section.dashboard")}
        isOpen={openSection === "dashboard"}
        onToggle={() => toggleSection("dashboard")}
      >
        <div data-testid="dashboard-section">
          {dashboardLoading ? (
            <p className="text-slate-400" data-testid="dashboard-loading">
              {t("common.loading")}
            </p>
          ) : dashboardError ? (
            <p className="text-red-400" data-testid="dashboard-error">
              {dashboardError}
            </p>
          ) : dashboard ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard
                label={t("admin.kpi.totalUsers")}
                value={dashboard.total_users}
                accent="cyan"
              />
              <KpiCard
                label={t("admin.kpi.activeUsers")}
                value={dashboard.active_users}
                accent="green"
              />
              <KpiCard
                label={t("admin.kpi.adminUsers")}
                value={dashboard.admin_users}
                accent="amber"
              />
              <KpiCard
                label={t("admin.kpi.creditsInCirculation")}
                value={dashboard.total_credits_in_circulation}
                accent="cyan"
              />
              <KpiCard
                label={t("admin.kpi.creditsGranted")}
                value={dashboard.total_credits_granted}
                accent="green"
              />
              <KpiCard
                label={t("admin.kpi.creditsSpent")}
                value={dashboard.total_credits_spent}
                accent="red"
              />
              <KpiCard
                label={t("admin.kpi.collectionEntries")}
                value={dashboard.total_collection_entries}
                accent="cyan"
              />
              <KpiCard
                label={t("admin.kpi.totalScans")}
                value={dashboard.total_scans}
                accent="green"
              />
            </div>
          ) : null}
        </div>
      </AccordionSection>

      {/* Liga Status Section */}
      <AccordionSection
        title={t("admin.section.ligaStatus")}
        isOpen={openSection === "liga-status"}
        onToggle={() => toggleSection("liga-status")}
      >
        <AdminLigaSection isOpen={openSection === "liga-status"} />
      </AccordionSection>

      {/* Schedules Section */}
      <AccordionSection
        title={t("admin.section.schedules")}
        isOpen={openSection === "schedules"}
        onToggle={() => toggleSection("schedules")}
      >
        <AdminSchedulesSection isOpen={openSection === "schedules"} />
      </AccordionSection>

      {/* Scans Section */}
      <AccordionSection
        title={t("admin.section.scans")}
        isOpen={openSection === "scans"}
        onToggle={() => toggleSection("scans")}
      >
        <AdminScansSection isOpen={openSection === "scans"} />
      </AccordionSection>

      {/* Errors Section */}
      <AccordionSection
        title={t("admin.section.errors")}
        isOpen={openSection === "errors"}
        onToggle={() => toggleSection("errors")}
      >
        <AdminErrorsSection isOpen={openSection === "errors"} />
      </AccordionSection>
    </div>
  );
}
