import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createSchedule,
  deleteSchedule,
  fetchSchedules,
  triggerSchedule,
  updateSchedule,
} from "../../api/schedules";
import { EmptyState } from "../EmptyState";
import { ScheduleForm } from "../ScheduleForm";
import { ScheduleTable } from "../ScheduleTable";
import type {
  ScheduleCreateRequest,
  ScheduleResponse,
  ScheduleUpdateRequest,
} from "../../types/api";

export function AdminSchedulesSection({ isOpen }: { isOpen: boolean }) {
  const { t } = useTranslation();
  const [schedules, setSchedules] = useState<ScheduleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingSchedule, setEditingSchedule] =
    useState<ScheduleResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [loaded, setLoaded] = useState(false);

  const loadSchedules = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetchSchedules();
      if (resp.data) {
        setSchedules(resp.data.schedules);
      } else if (resp.errors?.length) {
        setError(resp.errors[0].message);
      }
    } catch {
      setError(t("common.unknownError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  // Lazy load when section opens for the first time
  useEffect(() => {
    if (isOpen && !loaded) {
      setLoaded(true);
      loadSchedules();
    }
  }, [isOpen, loaded, loadSchedules]);

  async function handleCreate(data: ScheduleCreateRequest) {
    setSubmitting(true);
    setFeedback("");
    try {
      const resp = await createSchedule(data);
      if (resp.data) {
        setFeedback(t("schedules.created"));
        setShowForm(false);
        setEditingSchedule(null);
        await loadSchedules();
      } else if (resp.errors?.length) {
        setFeedback(resp.errors[0].message);
      }
    } catch {
      setFeedback(t("common.unknownError"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(data: ScheduleCreateRequest) {
    if (!editingSchedule) return;
    setSubmitting(true);
    setFeedback("");
    try {
      const updateData: ScheduleUpdateRequest = { ...data };
      const resp = await updateSchedule(editingSchedule.id, updateData);
      if (resp.data) {
        setFeedback(t("schedules.updated"));
        setShowForm(false);
        setEditingSchedule(null);
        await loadSchedules();
      } else if (resp.errors?.length) {
        setFeedback(resp.errors[0].message);
      }
    } catch {
      setFeedback(t("common.unknownError"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePauseResume(
    id: number,
    newStatus: "active" | "paused",
  ) {
    try {
      const resp = await updateSchedule(id, { status: newStatus });
      if (resp.data) {
        setFeedback(t("schedules.updated"));
        await loadSchedules();
      }
    } catch {
      setFeedback(t("common.unknownError"));
    }
  }

  async function handleTrigger(id: number) {
    try {
      const resp = await triggerSchedule(id);
      if (resp.data) {
        setFeedback(t("schedules.triggered"));
      } else if (resp.errors?.length) {
        setFeedback(resp.errors[0].message);
      }
    } catch {
      setFeedback(t("common.unknownError"));
    }
  }

  function handleEdit(schedule: ScheduleResponse) {
    setEditingSchedule(schedule);
    setShowForm(true);
  }

  async function handleDelete(id: number) {
    if (!confirm(t("schedules.deleteConfirm"))) return;
    try {
      await deleteSchedule(id);
      setFeedback(t("schedules.deleted"));
      await loadSchedules();
    } catch {
      setFeedback(t("common.unknownError"));
    }
  }

  function handleCancel() {
    setShowForm(false);
    setEditingSchedule(null);
  }

  if (!loaded) return null;

  return (
    <div data-testid="schedules-section">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-white">
          {t("schedules.title")}
        </h2>
        <button
          onClick={() => {
            setEditingSchedule(null);
            setShowForm(!showForm);
          }}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium transition-colors"
          data-testid="new-schedule-btn"
        >
          {showForm ? t("common.cancel") : t("schedules.new")}
        </button>
      </div>

      {/* Feedback */}
      {feedback && (
        <div
          className="mb-4 px-4 py-2 bg-slate-800 border border-slate-600 rounded text-sm text-slate-200"
          data-testid="schedule-feedback"
        >
          {feedback}
        </div>
      )}

      {/* Create/Edit Form */}
      {showForm && (
        <div className="mb-6" data-testid="schedule-form-container">
          <ScheduleForm
            initial={editingSchedule}
            onSubmit={editingSchedule ? handleUpdate : handleCreate}
            onCancel={handleCancel}
            submitting={submitting}
          />
        </div>
      )}

      {/* Loading */}
      {loading && (
        <p className="text-slate-400" data-testid="schedules-loading">
          {t("common.loading")}
        </p>
      )}

      {/* Error */}
      {error && (
        <p className="text-red-400" data-testid="schedules-error">
          {error}
        </p>
      )}

      {/* Empty state */}
      {!loading && !error && schedules.length === 0 && (
        <div data-testid="schedules-empty">
          <EmptyState
            message={t("schedules.empty")}
            compact
          />
        </div>
      )}

      {/* Schedule table */}
      {!loading && schedules.length > 0 && (
        <ScheduleTable
          schedules={schedules}
          onPauseResume={handlePauseResume}
          onTrigger={handleTrigger}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
