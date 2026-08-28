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
});
