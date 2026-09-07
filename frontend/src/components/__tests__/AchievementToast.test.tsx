import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AchievementToast } from "../AchievementToast";

describe("AchievementToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders title and description", () => {
    render(
      <AchievementToast
        title="First Card"
        description="Add your first card"
        icon="card"
        onDismiss={() => {}}
      />,
    );

    expect(screen.getByTestId("achievement-toast")).toBeInTheDocument();
    expect(screen.getByTestId("achievement-toast-title")).toHaveTextContent(
      "First Card",
    );
    expect(screen.getByText("Add your first card")).toBeInTheDocument();
  });

  it("renders with role=alert", () => {
    render(
      <AchievementToast
        title="Test"
        description="Test"
        icon="star"
        onDismiss={() => {}}
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("has a progress bar", () => {
    render(
      <AchievementToast
        title="Test"
        description="Test"
        icon="star"
        onDismiss={() => {}}
      />,
    );

    expect(screen.getByTestId("achievement-toast-progress")).toBeInTheDocument();
  });

  it("auto-dismisses after duration", () => {
    const onDismiss = vi.fn();
    render(
      <AchievementToast
        title="Test"
        description="Test"
        icon="star"
        durationMs={3000}
        onDismiss={onDismiss}
      />,
    );

    act(() => {
      vi.advanceTimersByTime(3100);
    });
    // After duration + exit animation (300ms)
    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("can be manually dismissed", () => {
    const onDismiss = vi.fn();
    render(
      <AchievementToast
        title="Test"
        description="Test"
        icon="star"
        durationMs={30000}
        onDismiss={onDismiss}
      />,
    );

    const dismissBtn = screen.getByTestId("achievement-toast-dismiss");
    fireEvent.click(dismissBtn);

    // Wait for exit animation
    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
