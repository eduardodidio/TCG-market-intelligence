import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuantityStepper } from "../../src/components/QuantityStepper";

describe("QuantityStepper", () => {
  it("renders current quantity", () => {
    render(<QuantityStepper value={3} onChange={vi.fn()} />);
    expect(screen.getByTestId("qty-value").textContent).toBe("3");
  });

  it("calls onChange with incremented value on + click", () => {
    const onChange = vi.fn();
    render(<QuantityStepper value={2} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("qty-plus"));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("calls onChange with decremented value on - click", () => {
    const onChange = vi.fn();
    render(<QuantityStepper value={3} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("qty-minus"));
    expect(onChange).toHaveBeenCalledWith(2);
  });

  it("disables minus button at min value (default 1)", () => {
    const onChange = vi.fn();
    render(<QuantityStepper value={1} onChange={onChange} />);
    const minusBtn = screen.getByTestId("qty-minus");
    expect(minusBtn.hasAttribute("disabled")).toBe(true);
    fireEvent.click(minusBtn);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("respects custom min value", () => {
    const onChange = vi.fn();
    render(<QuantityStepper value={5} onChange={onChange} min={5} />);
    const minusBtn = screen.getByTestId("qty-minus");
    expect(minusBtn.hasAttribute("disabled")).toBe(true);
  });

  it("shows label in non-compact mode", () => {
    render(<QuantityStepper value={1} onChange={vi.fn()} />);
    expect(screen.getByText("Qty")).toBeDefined();
  });

  it("hides label in compact mode", () => {
    render(<QuantityStepper value={1} onChange={vi.fn()} compact />);
    expect(screen.queryByText("Qty")).toBeNull();
  });

  it("renders stepper container", () => {
    render(<QuantityStepper value={1} onChange={vi.fn()} />);
    expect(screen.getByTestId("quantity-stepper")).toBeDefined();
  });
});
