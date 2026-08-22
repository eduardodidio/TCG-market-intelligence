import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScheduleForm } from "../../src/components/ScheduleForm";
import { makeSchedule } from "../fixtures/schedule-responses";

function renderForm(props = {}) {
  const defaults = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    ...props,
  };
  return {
    ...render(<ScheduleForm {...defaults} />),
    ...defaults,
  };
}

describe("ScheduleForm", () => {
  it("renders all form fields", () => {
    renderForm();

    expect(screen.getByTestId("schedule-name-input")).toBeDefined();
    expect(screen.getByTestId("schedule-cron-input")).toBeDefined();
    expect(screen.getByTestId("schedule-type-select")).toBeDefined();
    expect(screen.getByTestId("schedule-retries-input")).toBeDefined();
    expect(screen.getByTestId("schedule-submit-btn")).toBeDefined();
    expect(screen.getByTestId("schedule-cancel-btn")).toBeDefined();
  });

  it("pre-fills form when editing", () => {
    const schedule = makeSchedule({
      name: "Existing Schedule",
      cron_expression: "0 12 * * *",
    });
    renderForm({ initial: schedule });

    const nameInput = screen.getByTestId(
      "schedule-name-input",
    ) as HTMLInputElement;
    expect(nameInput.value).toBe("Existing Schedule");

    const cronInput = screen.getByTestId(
      "schedule-cron-input",
    ) as HTMLInputElement;
    expect(cronInput.value).toBe("0 12 * * *");
  });

  it("cron presets populate the cron field", () => {
    renderForm();

    const presets = screen.getByTestId("cron-presets");
    expect(presets).toBeDefined();

    // Click a preset
    const dailyPreset = screen.getByText("Daily 6am");
    fireEvent.click(dailyPreset);

    const cronInput = screen.getByTestId(
      "schedule-cron-input",
    ) as HTMLInputElement;
    expect(cronInput.value).toBe("0 6 * * *");
  });

  it("submits form with correct data", () => {
    const onSubmit = vi.fn();
    renderForm({ onSubmit });

    fireEvent.change(screen.getByTestId("schedule-name-input"), {
      target: { value: "Test Schedule" },
    });
    fireEvent.change(screen.getByTestId("schedule-cron-input"), {
      target: { value: "0 8 * * *" },
    });

    fireEvent.click(screen.getByTestId("schedule-submit-btn"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Test Schedule",
        cron_expression: "0 8 * * *",
        scan_type: "collection",
      }),
    );
  });

  it("shows error when name is empty", () => {
    const onSubmit = vi.fn();
    renderForm({ onSubmit });

    // Clear the default cron and name
    fireEvent.change(screen.getByTestId("schedule-name-input"), {
      target: { value: "" },
    });

    fireEvent.click(screen.getByTestId("schedule-submit-btn"));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByTestId("schedule-form-error")).toBeDefined();
  });

  it("cancel button calls onCancel", () => {
    const onCancel = vi.fn();
    renderForm({ onCancel });

    fireEvent.click(screen.getByTestId("schedule-cancel-btn"));
    expect(onCancel).toHaveBeenCalled();
  });
});
