import type { ScanRun, ScanListResponse } from "../../src/types/api";

export function makeScanRun(overrides: Partial<ScanRun> = {}): ScanRun {
  return {
    id: 1,
    scan_type: "collection",
    filters_json: "{}",
    status: "completed",
    cards_total: 100,
    cards_processed: 95,
    cards_failed: 5,
    observations_saved: 90,
    error_summary: null,
    started_at: "2026-08-20T10:00:00Z",
    finished_at: "2026-08-20T10:05:00Z",
    created_at: "2026-08-20T10:00:00Z",
    ...overrides,
  };
}

export function mockScanListResponse(
  scans?: ScanRun[],
  total?: number,
): ScanListResponse {
  const scanList = scans ?? [makeScanRun({ id: 1 }), makeScanRun({ id: 2, status: "running" })];
  return {
    scans: scanList,
    total: total ?? scanList.length,
  };
}
