import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PeriodSelector } from "../../src/components/PeriodSelector";

describe("PeriodSelector", () => {
  it("renders all default periods (7d, 30d, 90d)", () => {
    render(<PeriodSelector value="30d" onChange={() => {}} />);
    expect(screen.getByText("7d")).toBeDefined();
    expect(screen.getByText("30d")).toBeDefined();
    expect(screen.getByText("90d")).toBeDefined();
  });

  it("active period has bg-indigo-500 styling", () => {
    render(<PeriodSelector value="30d" onChange={() => {}} />);
    const activeBtn = screen.getByText("30d");
    expect(activeBtn).toHaveClass("bg-indigo-500");
  });

  it("inactive periods have bg-slate-800 styling", () => {
    render(<PeriodSelector value="30d" onChange={() => {}} />);
    const inactiveBtn = screen.getByText("7d");
    expect(inactiveBtn).toHaveClass("bg-slate-800");
    expect(inactiveBtn).not.toHaveClass("bg-indigo-500");
  });

  it("click calls onChange with the period string", () => {
    const onChange = vi.fn();
    render(<PeriodSelector value="30d" onChange={onChange} />);

    fireEvent.click(screen.getByText("7d"));
    expect(onChange).toHaveBeenCalledWith("7d");

    fireEvent.click(screen.getByText("90d"));
    expect(onChange).toHaveBeenCalledWith("90d");
  });

  it("renders custom periods when provided", () => {
    render(
      <PeriodSelector
        value="1d"
        onChange={() => {}}
        periods={["1d", "14d", "180d"]}
      />,
    );
    expect(screen.getByText("1d")).toBeDefined();
    expect(screen.getByText("14d")).toBeDefined();
    expect(screen.getByText("180d")).toBeDefined();
    expect(screen.queryByText("7d")).toBeNull();
    expect(screen.queryByText("30d")).toBeNull();
  });

  it("renders as a button group with role=group", () => {
    render(<PeriodSelector value="30d" onChange={() => {}} />);
    expect(screen.getByRole("group")).toBeDefined();
  });

  it("applies custom className", () => {
    const { container } = render(
      <PeriodSelector value="30d" onChange={() => {}} className="mt-4" />,
    );
    const group = container.querySelector("[role='group']");
    expect(group).toHaveClass("mt-4");
  });

  it("renders correct number of buttons", () => {
    render(<PeriodSelector value="30d" onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(3);
  });
});
