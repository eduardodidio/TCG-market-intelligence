import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Schedules } from "../../src/pages/Schedules";
import { mockScheduleListResponse } from "../fixtures/schedule-responses";

function renderSchedules() {
  return render(
    <MemoryRouter initialEntries={["/schedules"]}>
      <Schedules />
    </MemoryRouter>,
  );
}

describe("Schedules page", () => {
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

  it("renders page title and new schedule button", async () => {
    mockFetchSuccess();
    renderSchedules();

    await waitFor(() => {
      expect(screen.getByTestId("page-schedules")).toBeDefined();
    });

    expect(screen.getByText("Scheduled Scans")).toBeDefined();
    expect(screen.getByTestId("new-schedule-btn")).toBeDefined();
  });

  it("renders schedule table after loading", async () => {
    mockFetchSuccess();
    renderSchedules();

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

    renderSchedules();

    await waitFor(() => {
      expect(screen.getByTestId("schedules-empty")).toBeDefined();
    });

    expect(
      screen.getByText(
        "No schedules yet. Create one to automate your price scans.",
      ),
    ).toBeDefined();
  });

  it("toggle shows and hides the form", async () => {
    mockFetchSuccess();
    renderSchedules();

    await waitFor(() => {
      expect(screen.getByTestId("page-schedules")).toBeDefined();
    });

    // Form not visible initially
    expect(screen.queryByTestId("schedule-form-container")).toBeNull();

    // Click to show form
    fireEvent.click(screen.getByTestId("new-schedule-btn"));
    expect(screen.getByTestId("schedule-form-container")).toBeDefined();

    // Click again to hide form
    fireEvent.click(screen.getByTestId("new-schedule-btn"));
    expect(screen.queryByTestId("schedule-form-container")).toBeNull();
  });

  it("shows status badges with correct text", async () => {
    mockFetchSuccess();
    renderSchedules();

    await waitFor(() => {
      expect(screen.getByTestId("schedule-table")).toBeDefined();
    });

    expect(screen.getByTestId("status-badge-active")).toBeDefined();
    expect(screen.getByTestId("status-badge-paused")).toBeDefined();
  });
});
