import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MaxAgeDaysSelect } from "../../src/components/MaxAgeDaysSelect";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "collection.maxAgeDays": "Skip recently scanned",
        "collection.maxAgeDaysOption1": "Last 24 hours",
        "collection.maxAgeDaysOption3": "Last 3 days",
        "collection.maxAgeDaysOption7": "Last 7 days",
        "collection.maxAgeDaysOptionAll": "Scan all cards",
      };
      return map[key] ?? key;
    },
  }),
}));

describe("MaxAgeDaysSelect", () => {
  it("renders with label", () => {
    render(<MaxAgeDaysSelect value={1} onChange={vi.fn()} />);
    expect(screen.getByText("Skip recently scanned")).toBeTruthy();
  });

  it("renders all four options", () => {
    render(<MaxAgeDaysSelect value={1} onChange={vi.fn()} />);
    const dropdown = screen.getByTestId("max-age-days-dropdown") as HTMLSelectElement;
    expect(dropdown.options).toHaveLength(4);
    expect(dropdown.options[0].text).toBe("Last 24 hours");
    expect(dropdown.options[1].text).toBe("Last 3 days");
    expect(dropdown.options[2].text).toBe("Last 7 days");
    expect(dropdown.options[3].text).toBe("Scan all cards");
  });

  it("shows correct selected value for numeric option", () => {
    render(<MaxAgeDaysSelect value={3} onChange={vi.fn()} />);
    const dropdown = screen.getByTestId("max-age-days-dropdown") as HTMLSelectElement;
    expect(dropdown.value).toBe("3");
  });

  it('shows "all" when value is undefined', () => {
    render(<MaxAgeDaysSelect value={undefined} onChange={vi.fn()} />);
    const dropdown = screen.getByTestId("max-age-days-dropdown") as HTMLSelectElement;
    expect(dropdown.value).toBe("all");
  });

  it("calls onChange with numeric value when selecting a day option", () => {
    const onChange = vi.fn();
    render(<MaxAgeDaysSelect value={1} onChange={onChange} />);
    const dropdown = screen.getByTestId("max-age-days-dropdown");
    fireEvent.change(dropdown, { target: { value: "7" } });
    expect(onChange).toHaveBeenCalledWith(7);
  });

  it("calls onChange with undefined when selecting 'all'", () => {
    const onChange = vi.fn();
    render(<MaxAgeDaysSelect value={1} onChange={onChange} />);
    const dropdown = screen.getByTestId("max-age-days-dropdown");
    fireEvent.change(dropdown, { target: { value: "all" } });
    expect(onChange).toHaveBeenCalledWith(undefined);
  });

  it("disables select when disabled prop is true", () => {
    render(<MaxAgeDaysSelect value={1} onChange={vi.fn()} disabled />);
    const dropdown = screen.getByTestId("max-age-days-dropdown") as HTMLSelectElement;
    expect(dropdown.disabled).toBe(true);
  });

  it("is enabled by default", () => {
    render(<MaxAgeDaysSelect value={1} onChange={vi.fn()} />);
    const dropdown = screen.getByTestId("max-age-days-dropdown") as HTMLSelectElement;
    expect(dropdown.disabled).toBe(false);
  });
});
