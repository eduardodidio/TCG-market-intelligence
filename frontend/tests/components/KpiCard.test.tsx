import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KpiCard } from "../../src/components/KpiCard";

describe("KpiCard", () => {
  it("renders title and value", () => {
    render(<KpiCard title="Total Cards" value="150" />);

    expect(screen.getByText("Total Cards")).toBeDefined();
    expect(screen.getByText("150")).toBeDefined();
  });

  it("renders subtitle when provided", () => {
    render(
      <KpiCard title="Total Cards" value="150" subtitle="cards tracked" />,
    );

    expect(screen.getByText("cards tracked")).toBeDefined();
  });

  it("does not render subtitle when not provided", () => {
    render(<KpiCard title="Total Cards" value="150" />);

    expect(screen.queryByText("cards tracked")).toBeNull();
  });

  it("renders icon when provided", () => {
    render(
      <KpiCard
        title="Total Cards"
        value="150"
        icon={<span data-testid="test-icon">IC</span>}
      />,
    );

    expect(screen.getByTestId("test-icon")).toBeDefined();
  });

  it("applies correct data-testid", () => {
    render(<KpiCard title="Total Cards" value="150" />);

    expect(screen.getByTestId("kpi-card")).toBeDefined();
  });
});
