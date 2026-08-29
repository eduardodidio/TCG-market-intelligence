import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminSchedulesSection } from "../../../src/components/admin/AdminSchedulesSection";
import { mockScheduleListResponse } from "../../fixtures/schedule-responses";

function renderSection(isOpen = true) {
  return render(
    <MemoryRouter>
      <AdminSchedulesSection isOpen={isOpen} />
    </MemoryRouter>,
  );
}

describe("AdminSchedulesSection", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchSuccess() {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: mockScheduleListResponse(),
          meta: { request_id: "test" },
          errors: [],
        }),
    }) as unknown as typeof fetch;
  }

  it("renders nothing when isOpen is false and never opened", () => {
    mockFetchSuccess();
    renderSection(false);
    expect(screen.queryByTestId("schedules-section")).not.toBeInTheDocument();
  });

  it("renders section content when isOpen is true", async () => {
    mockFetchSuccess();
    renderSection(true);
    await waitFor(() => {
      expect(screen.getByTestId("schedules-section")).toBeInTheDocument();
    });
  });

  it("renders schedule table after loading", async () => {
    mockFetchSuccess();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("schedule-table")).toBeDefined();
    });

    expect(screen.getByTestId("schedule-row-1")).toBeDefined();
    expect(screen.getByTestId("schedule-row-2")).toBeDefined();
  });

  it("shows empty state when no schedules", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { schedules: [], total: 0 },
          meta: { request_id: "test" },
          errors: [],
        }),
    }) as unknown as typeof fetch;

    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("schedules-empty")).toBeDefined();
    });
  });

  it("renders new schedule button", async () => {
    mockFetchSuccess();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("new-schedule-btn")).toBeDefined();
    });
  });

  it("toggle shows and hides the form", async () => {
    mockFetchSuccess();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("schedules-section")).toBeDefined();
    });

    expect(screen.queryByTestId("schedule-form-container")).toBeNull();

    fireEvent.click(screen.getByTestId("new-schedule-btn"));
    expect(screen.getByTestId("schedule-form-container")).toBeDefined();

    fireEvent.click(screen.getByTestId("new-schedule-btn"));
    expect(screen.queryByTestId("schedule-form-container")).toBeNull();
  });

  it("handleCreate: successful create closes form and reloads list", async () => {
    let callCount = 0;
    globalThis.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      callCount++;
      const method = init?.method ?? "GET";

      // POST = create schedule
      if (method === "POST") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              data: {
                id: 99,
                name: "New Schedule",
                description: null,
                cron_expression: "0 6 * * *",
                scan_type: "collection",
                filters_json: "{}",
                status: "active",
                last_run_id: null,
                last_run_at: null,
                next_run_at: null,
                error_count: 0,
                max_retries: 3,
                created_at: "2026-08-29T00:00:00",
                updated_at: "2026-08-29T00:00:00",
              },
              meta: { request_id: "create-test" },
              errors: [],
            }),
        });
      }

      // GET = list schedules (initial load + reload after create)
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: mockScheduleListResponse(),
            meta: { request_id: "list-test" },
            errors: [],
          }),
      });
    }) as unknown as typeof fetch;

    renderSection(true);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByTestId("schedules-section")).toBeDefined();
    });

    // Open form
    fireEvent.click(screen.getByTestId("new-schedule-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("schedule-form")).toBeDefined();
    });

    // Fill the name field
    fireEvent.change(screen.getByTestId("schedule-name-input"), {
      target: { value: "New Schedule" },
    });

    // Submit
    fireEvent.click(screen.getByTestId("schedule-submit-btn"));

    // Form should close and feedback should appear
    await waitFor(() => {
      expect(screen.queryByTestId("schedule-form-container")).toBeNull();
    });
    await waitFor(() => {
      expect(screen.getByTestId("schedule-feedback")).toBeDefined();
    });
  });

  it("handleCreate: shows error feedback when API returns errors", async () => {
    let firstCall = true;
    globalThis.fetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";

      if (method === "POST") {
        // Simulate a 422 validation error
        return Promise.resolve({
          ok: false,
          status: 422,
          statusText: "Unprocessable Entity",
          json: () =>
            Promise.resolve({ detail: "Invalid cron expression" }),
        });
      }

      // GET = list
      if (firstCall) {
        firstCall = false;
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              data: { schedules: [], total: 0 },
              meta: { request_id: "list" },
              errors: [],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: { schedules: [], total: 0 },
            meta: { request_id: "list" },
            errors: [],
          }),
      });
    }) as unknown as typeof fetch;

    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("schedules-section")).toBeDefined();
    });

    // Open form
    fireEvent.click(screen.getByTestId("new-schedule-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("schedule-form")).toBeDefined();
    });

    // Fill the name
    fireEvent.change(screen.getByTestId("schedule-name-input"), {
      target: { value: "Bad Schedule" },
    });

    // Submit
    fireEvent.click(screen.getByTestId("schedule-submit-btn"));

    // Error feedback should appear, form should remain open
    await waitFor(() => {
      expect(screen.getByTestId("schedule-feedback")).toBeDefined();
    });
    expect(screen.getByTestId("schedule-feedback").textContent).toContain(
      "Invalid cron expression",
    );
  });

  it("handleUpdate: successful update closes form and reloads", async () => {
    // Start with one schedule in the list
    globalThis.fetch = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";

      if (method === "PATCH") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              data: {
                id: 1,
                name: "Updated Name",
                description: null,
                cron_expression: "0 6 * * *",
                scan_type: "collection",
                filters_json: "{}",
                status: "active",
                last_run_id: null,
                last_run_at: null,
                next_run_at: null,
                error_count: 0,
                max_retries: 3,
                created_at: "2026-08-29T00:00:00",
                updated_at: "2026-08-29T00:00:00",
              },
              meta: { request_id: "update-test" },
              errors: [],
            }),
        });
      }

      // GET = list
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: mockScheduleListResponse(),
            meta: { request_id: "list-test" },
            errors: [],
          }),
      });
    }) as unknown as typeof fetch;

    renderSection(true);

    // Wait for table to render
    await waitFor(() => {
      expect(screen.getByTestId("schedule-row-1")).toBeDefined();
    });

    // Click the edit button on the first schedule
    const editBtn = screen.getByTestId("action-edit-1");
    fireEvent.click(editBtn);

    // Form should open with prefilled data
    await waitFor(() => {
      expect(screen.getByTestId("schedule-form")).toBeDefined();
    });

    // Change the name
    fireEvent.change(screen.getByTestId("schedule-name-input"), {
      target: { value: "Updated Name" },
    });

    // Submit
    fireEvent.click(screen.getByTestId("schedule-submit-btn"));

    // Form should close
    await waitFor(() => {
      expect(screen.queryByTestId("schedule-form-container")).toBeNull();
    });
    // Feedback should appear
    await waitFor(() => {
      expect(screen.getByTestId("schedule-feedback")).toBeDefined();
    });
  });
});
