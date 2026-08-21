import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Layout } from "../../src/components/Layout";

function renderLayout(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Layout />
    </MemoryRouter>,
  );
}

describe("Layout", () => {
  it("renders the sidebar with navigation links", () => {
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    expect(nav).toBeDefined();

    const links = nav.querySelectorAll("a");
    expect(links).toHaveLength(5);

    const linkTexts = Array.from(links).map((a) => a.textContent);
    expect(linkTexts).toContain("Dashboard");
    expect(linkTexts).toContain("My Collection");
    expect(linkTexts).toContain("Explore Cards");
    expect(linkTexts).toContain("Market Movers");
    expect(linkTexts).toContain("Price Scans");
  });

  it("renders the main content area (Outlet)", () => {
    renderLayout();
    const main = screen.getByTestId("main-content");
    expect(main).toBeDefined();
  });

  it("renders the sidebar element", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toBeDefined();
  });

  it("renders a hamburger button for mobile", () => {
    renderLayout();
    const hamburger = screen.getByTestId("hamburger-button");
    expect(hamburger).toBeDefined();
    expect(hamburger.getAttribute("aria-label")).toBe("Toggle navigation");
  });

  it("renders the app title", () => {
    renderLayout();
    // Title appears in both sidebar and mobile header
    const titles = screen.getAllByText("TCG Market");
    expect(titles.length).toBeGreaterThanOrEqual(1);
  });

  it("links have correct href attributes", () => {
    renderLayout();
    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");

    const hrefs = Array.from(links).map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/collection");
    expect(hrefs).toContain("/cards");
    expect(hrefs).toContain("/market/movers");
    expect(hrefs).toContain("/scans");
  });

  // --- F07-T07: Responsive toggle tests ---

  it("hamburger button toggles sidebar visibility", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    const hamburger = screen.getByTestId("hamburger-button");

    // Initially sidebar is hidden (has -translate-x-full)
    expect(sidebar.className).toContain("-translate-x-full");

    // Click hamburger to open
    fireEvent.click(hamburger);
    expect(sidebar.className).toContain("translate-x-0");
    expect(sidebar.className).not.toContain("-translate-x-full");

    // Click hamburger again to close
    fireEvent.click(hamburger);
    expect(sidebar.className).toContain("-translate-x-full");
  });

  it("clicking overlay closes sidebar", () => {
    renderLayout();
    const hamburger = screen.getByTestId("hamburger-button");

    // Open sidebar
    fireEvent.click(hamburger);
    const overlay = screen.getByTestId("sidebar-overlay");
    expect(overlay).toBeDefined();

    // Click overlay to close
    fireEvent.click(overlay);
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("-translate-x-full");
  });

  // --- F15-T03: BRL currency indicator tests ---

  it("renders BRL text in sidebar", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    const brlElement = sidebar.querySelector("span");
    const brlTexts = Array.from(sidebar.querySelectorAll("span")).filter(
      (el) => el.textContent === "BRL",
    );
    expect(brlTexts.length).toBeGreaterThanOrEqual(1);
  });

  it("renders element with aria-label 'Brazilian flag'", () => {
    renderLayout();
    const flag = screen.getByLabelText("Brazilian flag");
    expect(flag).toBeDefined();
    expect(flag.getAttribute("role")).toBe("img");
  });

  it("currency indicator is present in the DOM on initial render", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    const flag = screen.getByLabelText("Brazilian flag");
    const brl = screen.getByText("BRL");
    // Both elements should be within the sidebar
    expect(sidebar.contains(flag)).toBe(true);
    expect(sidebar.contains(brl)).toBe(true);
  });

  it("nav links have focus-visible ring classes", () => {
    renderLayout();
    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");

    links.forEach((link) => {
      expect(link.className).toContain("focus-visible:ring-2");
      expect(link.className).toContain("focus-visible:ring-cyan-400");
    });
  });
});
