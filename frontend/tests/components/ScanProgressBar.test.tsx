import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ScanProgressBar } from "../../src/components/ScanProgressBar";

describe("ScanProgressBar", () => {
  const baseProps = {
    processed: 0,
    total: 10,
    priceFoundCount: 0,
    startTime: Date.now(),
    isRefreshing: true,
    isDone: false,
    error: null,
  };

  it("renders progress bar with percentage", () => {
    render(<ScanProgressBar {...baseProps} processed={5} total={10} />);
    expect(screen.getByTestId("scan-progress-text")).toHaveTextContent("5/10 (50%)");
  });

  it("renders progress bar fill width", () => {
    render(<ScanProgressBar {...baseProps} processed={3} total={10} />);
    const fill = screen.getByTestId("scan-progress-fill");
    expect(fill).toHaveStyle({ width: "30%" });
  });

  it("displays current card name", () => {
    render(<ScanProgressBar {...baseProps} currentCardName="Lightning Bolt" />);
    expect(screen.getByTestId("scan-current-card")).toHaveTextContent("Scanning: \"Lightning Bolt\"");
  });

  it("displays connecting message when no card name", () => {
    render(<ScanProgressBar {...baseProps} />);
    expect(screen.getByText("Connecting to scan stream...")).toBeInTheDocument();
  });

  it("displays price-found ratio", () => {
    render(<ScanProgressBar {...baseProps} processed={10} priceFoundCount={8} />);
    expect(screen.getByTestId("scan-prices-found")).toHaveTextContent("Prices found: 8/10");
  });

  it("displays ETA after 3+ cards processed", () => {
    const startTime = Date.now() - 6000; // 6 seconds ago
    render(<ScanProgressBar {...baseProps} processed={3} total={10} startTime={startTime} />);
    expect(screen.getByTestId("scan-eta")).toBeInTheDocument();
  });

  it("hides ETA when processed < 3", () => {
    render(<ScanProgressBar {...baseProps} processed={2} total={10} />);
    expect(screen.queryByTestId("scan-eta")).not.toBeInTheDocument();
  });

  it("shows completion state with green checkmark", () => {
    render(
      <ScanProgressBar
        {...baseProps}
        isRefreshing={false}
        isDone={true}
        processed={10}
        total={10}
        priceFoundCount={8}
      />,
    );
    expect(screen.getByTestId("scan-progress-done")).toBeInTheDocument();
    expect(screen.getByText(/Scan complete: 10 cards, 8 prices updated/)).toBeInTheDocument();
  });

  it("shows error state", () => {
    render(
      <ScanProgressBar
        {...baseProps}
        isRefreshing={false}
        error="Connection timeout"
      />,
    );
    expect(screen.getByTestId("scan-progress-error")).toBeInTheDocument();
    expect(screen.getByText(/Connection timeout/)).toBeInTheDocument();
  });

  it("renders nothing when not refreshing and not done and no error", () => {
    const { container } = render(
      <ScanProgressBar
        {...baseProps}
        isRefreshing={false}
        isDone={false}
        error={null}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows cancel button when onCancel is provided", () => {
    const onCancel = vi.fn();
    render(<ScanProgressBar {...baseProps} onCancel={onCancel} />);
    expect(screen.getByTestId("scan-cancel-btn")).toBeInTheDocument();
  });

  it("hides cancel button when onCancel is not provided", () => {
    render(<ScanProgressBar {...baseProps} />);
    expect(screen.queryByTestId("scan-cancel-btn")).not.toBeInTheDocument();
  });
});
