import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { GauchoDialog } from "../../src/components/GauchoDialog";

describe("GauchoDialog", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders message text", () => {
    render(<GauchoDialog message="Bah meu!" onDismiss={vi.fn()} />);
    expect(screen.getByTestId("gaucho-message").textContent).toBe("Bah meu!");
  });

  it("renders option buttons when provided", () => {
    const options = [
      { label: "sim", reply: "dale!" },
      { label: "nao", reply: "barbaridade!" },
    ];
    render(
      <GauchoDialog message="Tche?" options={options} onDismiss={vi.fn()} />,
    );
    expect(screen.getByTestId("gaucho-option-sim")).toBeDefined();
    expect(screen.getByTestId("gaucho-option-nao")).toBeDefined();
  });

  it("clicking option shows reply text", () => {
    const options = [{ label: "sim", reply: "dale!" }];
    render(
      <GauchoDialog message="Tche?" options={options} onDismiss={vi.fn()} />,
    );
    fireEvent.click(screen.getByTestId("gaucho-option-sim"));
    expect(screen.getByTestId("gaucho-reply").textContent).toBe("dale!");
  });

  it("auto-dismisses when no options after timeout", () => {
    const onDismiss = vi.fn();
    render(
      <GauchoDialog message="Auto msg" autoDismissMs={3000} onDismiss={onDismiss} />,
    );
    expect(onDismiss).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("calls onDismiss after reply timeout", () => {
    const onDismiss = vi.fn();
    const options = [{ label: "ok", reply: "nice" }];
    render(
      <GauchoDialog message="Hey" options={options} onDismiss={onDismiss} />,
    );
    fireEvent.click(screen.getByTestId("gaucho-option-ok"));
    expect(onDismiss).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(4500);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("close button dismisses dialog", () => {
    const onDismiss = vi.fn();
    render(<GauchoDialog message="Bah" onDismiss={onDismiss} />);
    fireEvent.click(screen.getByTestId("gaucho-dialog-close"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("does not auto-dismiss when options are provided", () => {
    const onDismiss = vi.fn();
    const options = [{ label: "ok", reply: "nice" }];
    render(
      <GauchoDialog
        message="Hey"
        options={options}
        autoDismissMs={1000}
        onDismiss={onDismiss}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("option without reply dismisses directly", () => {
    const onDismiss = vi.fn();
    const options = [{ label: "ahaaam!" }];
    render(
      <GauchoDialog message="Bah" options={options} onDismiss={onDismiss} />,
    );
    fireEvent.click(screen.getByTestId("gaucho-option-ahaaam!"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
