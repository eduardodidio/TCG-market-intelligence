import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScanHistoryTable } from "../../src/components/ScanHistoryTable";
import { makeScanRun } from "../fixtures/scan-responses";

describe("ScanHistoryTable", () => {
  it("renders rows from data", () => {
    const scans = [
      makeScanRun({ id: 1, scan_type: "collection", status: "completed" }),
      makeScanRun({ id: 2, scan_type: "set", status: "running" }),
    ];

    render(<ScanHistoryTable scans={scans} />);

    expect(screen.getByTestId("scans-table")).toBeDefined();
    expect(screen.getByTestId("scan-row-1")).toBeDefined();
    expect(screen.getByTestId("scan-row-2")).toBeDefined();
  });

  it("renders correct status badge colors", () => {
    const scans = [
      makeScanRun({ id: 1, status: "completed" }),
      makeScanRun({ id: 2, status: "failed" }),
      makeScanRun({ id: 3, status: "running" }),
      makeScanRun({ id: 4, status: "pending" }),
    ];

    render(<ScanHistoryTable scans={scans} />);

    const completedBadge = screen.getByTestId("status-badge-completed");
    expect(completedBadge.className).toContain("bg-green-100");
    expect(completedBadge.className).toContain("text-green-700");

    const failedBadge = screen.getByTestId("status-badge-failed");
    expect(failedBadge.className).toContain("bg-red-100");
    expect(failedBadge.className).toContain("text-red-700");

    const runningBadge = screen.getByTestId("status-badge-running");
    expect(runningBadge.className).toContain("bg-blue-100");
    expect(runningBadge.className).toContain("text-blue-700");

    const pendingBadge = screen.getByTestId("status-badge-pending");
    expect(pendingBadge.className).toContain("bg-gray-100");
    expect(pendingBadge.className).toContain("text-gray-700");
  });

  it("shows empty state message when no scans", () => {
    render(<ScanHistoryTable scans={[]} />);

    expect(screen.getByTestId("scans-empty")).toBeDefined();
    expect(screen.getByText("No scan runs yet.")).toBeDefined();
  });

  it("calls onSelect when a row is clicked", () => {
    const onSelect = vi.fn();
    const scans = [makeScanRun({ id: 5 })];

    render(<ScanHistoryTable scans={scans} onSelect={onSelect} />);

    fireEvent.click(screen.getByTestId("scan-row-5"));
    expect(onSelect).toHaveBeenCalledWith(5);
  });
});
