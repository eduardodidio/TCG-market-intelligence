import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScheduleTable } from "../../src/components/ScheduleTable";
import { makeSchedule } from "../fixtures/schedule-responses";

function renderTable(schedules = [makeSchedule()], handlers = {}) {
  const defaultHandlers = {
    onPauseResume: vi.fn(),
    onTrigger: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    ...handlers,
  };
  return {
    ...render(
      <ScheduleTable schedules={schedules} {...defaultHandlers} />,
    ),
    ...defaultHandlers,
  };
}

describe("ScheduleTable", () => {
  it("renders rows for each schedule", () => {
    const schedules = [
      makeSchedule({ id: 1, name: "Schedule A" }),
      makeSchedule({ id: 2, name: "Schedule B" }),
    ];
    renderTable(schedules);

    expect(screen.getByTestId("schedule-row-1")).toBeDefined();
    expect(screen.getByTestId("schedule-row-2")).toBeDefined();
    expect(screen.getByText("Schedule A")).toBeDefined();
    expect(screen.getByText("Schedule B")).toBeDefined();
  });

  it("displays status badge with correct color class", () => {
    renderTable([makeSchedule({ id: 1, status: "active" })]);
    const badge = screen.getByTestId("status-badge-active");
    expect(badge).toBeDefined();
    expect(badge.textContent).toBe("Active");
  });

  it("displays error count in N/max format", () => {
    renderTable([
      makeSchedule({ id: 1, error_count: 2, max_retries: 3 }),
    ]);
    expect(screen.getByText("2/3")).toBeDefined();
  });

  it("error count is red when at max", () => {
    renderTable([
      makeSchedule({ id: 1, error_count: 3, max_retries: 3 }),
    ]);
    const el = screen.getByText("3/3");
    expect(el.className).toContain("text-red-400");
  });

  it("pause button triggers onPauseResume", () => {
    const onPauseResume = vi.fn();
    renderTable(
      [makeSchedule({ id: 1, status: "active" })],
      { onPauseResume },
    );

    fireEvent.click(screen.getByTestId("action-pause-1"));
    expect(onPauseResume).toHaveBeenCalledWith(1, "paused");
  });

  it("resume button triggers onPauseResume with active", () => {
    const onPauseResume = vi.fn();
    renderTable(
      [makeSchedule({ id: 1, status: "paused" })],
      { onPauseResume },
    );

    fireEvent.click(screen.getByTestId("action-pause-1"));
    expect(onPauseResume).toHaveBeenCalledWith(1, "active");
  });

  it("trigger button calls onTrigger", () => {
    const onTrigger = vi.fn();
    renderTable([makeSchedule({ id: 1 })], { onTrigger });

    fireEvent.click(screen.getByTestId("action-trigger-1"));
    expect(onTrigger).toHaveBeenCalledWith(1);
  });

  it("edit button calls onEdit", () => {
    const schedule = makeSchedule({ id: 1 });
    const onEdit = vi.fn();
    renderTable([schedule], { onEdit });

    fireEvent.click(screen.getByTestId("action-edit-1"));
    expect(onEdit).toHaveBeenCalledWith(schedule);
  });

  it("delete button calls onDelete", () => {
    const onDelete = vi.fn();
    renderTable([makeSchedule({ id: 1 })], { onDelete });

    fireEvent.click(screen.getByTestId("action-delete-1"));
    expect(onDelete).toHaveBeenCalledWith(1);
  });

  // F96-T05: Credit-pause indicator tests
  it("renders red badge for paused_insufficient_credits status", () => {
    renderTable([
      makeSchedule({ id: 1, status: "paused_insufficient_credits" }),
    ]);
    const badge = screen.getByTestId(
      "status-badge-paused_insufficient_credits",
    );
    expect(badge).toBeDefined();
    expect(badge.className).toContain("text-red-400");
    expect(badge.className).toContain("bg-red-500/20");
    expect(badge.textContent).toContain("Insufficient tokens");
  });

  it("renders warning icon for paused_insufficient_credits", () => {
    renderTable([
      makeSchedule({ id: 1, status: "paused_insufficient_credits" }),
    ]);
    const icon = screen.getByTestId("credit-pause-warning-icon");
    expect(icon).toBeDefined();
  });

  it("does NOT render warning icon for regular paused status", () => {
    renderTable([
      makeSchedule({ id: 1, status: "paused" }),
    ]);
    expect(screen.queryByTestId("credit-pause-warning-icon")).toBeNull();
  });

  it("renders recovery hint for paused_insufficient_credits", () => {
    renderTable([
      makeSchedule({ id: 1, status: "paused_insufficient_credits" }),
    ]);
    const hint = screen.getByTestId("credit-pause-hint-1");
    expect(hint).toBeDefined();
    expect(hint.textContent).toContain("Claim bonus or add tokens to resume");
  });

  it("tooltip includes recovery advice for credit-paused schedule", () => {
    renderTable([
      makeSchedule({ id: 1, status: "paused_insufficient_credits" }),
    ]);
    const badge = screen.getByTestId(
      "status-badge-paused_insufficient_credits",
    );
    expect(badge.getAttribute("title")).toContain("Claim your bonus");
  });

  it("resume button works for paused_insufficient_credits", () => {
    const onPauseResume = vi.fn();
    renderTable(
      [makeSchedule({ id: 1, status: "paused_insufficient_credits" })],
      { onPauseResume },
    );

    fireEvent.click(screen.getByTestId("action-pause-1"));
    expect(onPauseResume).toHaveBeenCalledWith(1, "active");
  });
});
