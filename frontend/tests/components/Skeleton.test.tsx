import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  SkeletonKpi,
  SkeletonCard,
  SkeletonTable,
  SkeletonChartPanel,
  SkeletonInfoPanel,
} from "../../src/components/Skeleton";

describe("Skeleton components", () => {
  it("SkeletonKpi renders with animate-pulse class", () => {
    render(<SkeletonKpi />);
    const el = screen.getByTestId("skeleton-kpi");
    expect(el).toBeDefined();
    // The children should have animate-pulse
    const pulsingElements = el.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it("SkeletonCard renders with animate-pulse class", () => {
    render(<SkeletonCard />);
    const el = screen.getByTestId("skeleton-card");
    expect(el).toBeDefined();
    const pulsingElements = el.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it("SkeletonCard uses aspect-[5/7] instead of h-40 for CLS-safe sizing", () => {
    render(<SkeletonCard />);
    const el = screen.getByTestId("skeleton-card");
    // The image placeholder should use aspect ratio, not fixed height
    const imageArea = el.querySelector(".aspect-\\[5\\/7\\]");
    expect(imageArea).not.toBeNull();
    // h-40 should NOT be present anywhere in the skeleton
    const fixedHeight = el.querySelector(".h-40");
    expect(fixedHeight).toBeNull();
  });

  it("SkeletonCard has an info section with two pulse bars below image area", () => {
    render(<SkeletonCard />);
    const infoSection = screen.getByTestId("skeleton-card-info");
    expect(infoSection).toBeDefined();
    // Info section should contain two pulse bars
    const pulseBars = infoSection.querySelectorAll(".animate-pulse");
    expect(pulseBars.length).toBe(2);
  });

  it("SkeletonTable renders with animate-pulse class", () => {
    render(<SkeletonTable />);
    const el = screen.getByTestId("skeleton-table");
    expect(el).toBeDefined();
    const pulsingElements = el.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it("SkeletonTable renders custom number of rows", () => {
    render(<SkeletonTable rows={3} />);
    const el = screen.getByTestId("skeleton-table");
    // Each row has a border-b on the container div
    const rows = el.querySelectorAll(".animate-pulse.h-4.w-6");
    expect(rows.length).toBe(3);
  });

  it("SkeletonChartPanel renders with animate-pulse class", () => {
    render(<SkeletonChartPanel />);
    const el = screen.getByTestId("skeleton-chart");
    expect(el).toBeDefined();
    const pulsingElements = el.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it("SkeletonInfoPanel renders with animate-pulse class", () => {
    render(<SkeletonInfoPanel />);
    const el = screen.getByTestId("skeleton-info");
    expect(el).toBeDefined();
    const pulsingElements = el.querySelectorAll(".animate-pulse");
    expect(pulsingElements.length).toBeGreaterThan(0);
  });
});
