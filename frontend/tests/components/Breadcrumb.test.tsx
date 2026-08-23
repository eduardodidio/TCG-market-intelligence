import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Breadcrumb } from "../../src/components/Breadcrumb";

function renderBreadcrumb(items: { label: string; to?: string }[]) {
  return render(
    <MemoryRouter>
      <Breadcrumb items={items} />
    </MemoryRouter>,
  );
}

describe("Breadcrumb", () => {
  it("renders breadcrumb nav", () => {
    renderBreadcrumb([
      { label: "Collection", to: "/collection" },
      { label: "Lightning Bolt" },
    ]);

    const nav = screen.getByTestId("breadcrumb");
    expect(nav).toBeDefined();
    expect(nav.getAttribute("aria-label")).toBe("Breadcrumb");
  });

  it("renders link items as links", () => {
    renderBreadcrumb([
      { label: "Collection", to: "/collection" },
      { label: "Lightning Bolt" },
    ]);

    const link = screen.getByText("Collection");
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe("/collection");
  });

  it("renders final item as text (not link)", () => {
    renderBreadcrumb([
      { label: "Collection", to: "/collection" },
      { label: "Lightning Bolt" },
    ]);

    const current = screen.getByText("Lightning Bolt");
    expect(current.tagName).toBe("SPAN");
  });

  it("renders single item without separator", () => {
    renderBreadcrumb([{ label: "Home" }]);

    expect(screen.getByText("Home")).toBeDefined();
    const svgs = screen.getByTestId("breadcrumb").querySelectorAll("svg");
    expect(svgs).toHaveLength(0);
  });

  it("renders separators between items", () => {
    renderBreadcrumb([
      { label: "A", to: "/a" },
      { label: "B", to: "/b" },
      { label: "C" },
    ]);

    // 2 separators for 3 items
    const svgs = screen.getByTestId("breadcrumb").querySelectorAll("svg");
    expect(svgs).toHaveLength(2);
  });
});
