import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AccordionSection } from "../../src/components/AccordionSection";

describe("AccordionSection", () => {
  it("renders title", () => {
    render(
      <AccordionSection title="Test Section" isOpen={false} onToggle={vi.fn()}>
        <p>Content</p>
      </AccordionSection>,
    );
    expect(screen.getByText("Test Section")).toBeInTheDocument();
  });

  it("calls onToggle when header is clicked", () => {
    const onToggle = vi.fn();
    render(
      <AccordionSection title="Test Section" isOpen={false} onToggle={onToggle}>
        <p>Content</p>
      </AccordionSection>,
    );
    fireEvent.click(screen.getByText("Test Section"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("shows children when isOpen is true", () => {
    render(
      <AccordionSection title="Test Section" isOpen={true} onToggle={vi.fn()}>
        <p>Visible Content</p>
      </AccordionSection>,
    );
    expect(screen.getByText("Visible Content")).toBeInTheDocument();
    expect(screen.getByTestId("accordion-content")).toBeInTheDocument();
  });

  it("hides children when isOpen is false", () => {
    render(
      <AccordionSection title="Test Section" isOpen={false} onToggle={vi.fn()}>
        <p>Hidden Content</p>
      </AccordionSection>,
    );
    expect(screen.queryByText("Hidden Content")).not.toBeInTheDocument();
    expect(screen.queryByTestId("accordion-content")).not.toBeInTheDocument();
  });

  it("chevron has rotate-180 class when open", () => {
    const { rerender } = render(
      <AccordionSection title="Test Section" isOpen={true} onToggle={vi.fn()}>
        <p>Content</p>
      </AccordionSection>,
    );
    const chevron = screen.getByTestId("accordion-chevron");
    // SVG elements use getAttribute for class in jsdom
    const getClass = (el: Element) =>
      el.getAttribute("class") ?? "";
    expect(getClass(chevron)).toContain("rotate-180");

    rerender(
      <AccordionSection title="Test Section" isOpen={false} onToggle={vi.fn()}>
        <p>Content</p>
      </AccordionSection>,
    );
    expect(getClass(chevron)).not.toContain("rotate-180");
  });

  it("renders icon when provided", () => {
    render(
      <AccordionSection
        title="With Icon"
        icon={<span data-testid="custom-icon">*</span>}
        isOpen={false}
        onToggle={vi.fn()}
      >
        <p>Content</p>
      </AccordionSection>,
    );
    expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
  });

  it("generates data-testid from title", () => {
    render(
      <AccordionSection title="Liga Status" isOpen={false} onToggle={vi.fn()}>
        <p>Content</p>
      </AccordionSection>,
    );
    expect(screen.getByTestId("accordion-liga-status")).toBeInTheDocument();
    expect(screen.getByTestId("accordion-toggle-liga-status")).toBeInTheDocument();
  });
});
