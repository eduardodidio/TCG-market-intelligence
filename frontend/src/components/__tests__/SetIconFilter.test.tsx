import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SetIconFilter } from "../SetIconFilter";

// Mock scryfallSetIconUrl
vi.mock("../../utils/scryfall", () => ({
  scryfallSetIconUrl: (code: string) => `https://scryfall.com/sets/${code}.svg`,
}));

// Mock ResizeObserver (jsdom does not provide it)
class MockResizeObserver {
  observe() {}
  disconnect() {}
  unobserve() {}
}
globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

function makeOptions(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    label: `Set ${i + 1}`,
    value: `set${i + 1}`,
  }));
}

/** Helper to set scroll dimensions on the scroll container. */
function mockScrollDimensions(
  container: HTMLElement,
  { scrollWidth, clientWidth, scrollLeft }: { scrollWidth: number; clientWidth: number; scrollLeft: number },
) {
  Object.defineProperty(container, "scrollWidth", { value: scrollWidth, configurable: true });
  Object.defineProperty(container, "clientWidth", { value: clientWidth, configurable: true });
  Object.defineProperty(container, "scrollLeft", { value: scrollLeft, configurable: true, writable: true });
}

describe("SetIconFilter", () => {
  const defaultProps = {
    options: makeOptions(5),
    selected: null as string | null,
    onSelect: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all icons in a scrollable container", () => {
    render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
    const container = screen.getByTestId("scroll-container");
    expect(container).toBeInTheDocument();
    // 20 set icons + "All" button
    expect(container.children.length).toBe(21);
  });

  it("renders the 'All' button as first child", () => {
    render(<SetIconFilter {...defaultProps} />);
    const container = screen.getByTestId("scroll-container");
    const firstButton = container.children[0] as HTMLButtonElement;
    expect(firstButton.textContent).toBe("All");
  });

  it("'All' button is always visible regardless of option count", () => {
    render(<SetIconFilter {...defaultProps} options={makeOptions(30)} />);
    const container = screen.getByTestId("scroll-container");
    const allButton = container.children[0] as HTMLButtonElement;
    expect(allButton.textContent).toBe("All");
    expect(allButton).toBeVisible();
  });

  it("has a max-width constraint on the scroll container", () => {
    render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
    const container = screen.getByTestId("scroll-container");
    expect(container.className).toContain("max-w-[520px]");
  });

  it("scroll container has overflow-x-auto", () => {
    render(<SetIconFilter {...defaultProps} />);
    const container = screen.getByTestId("scroll-container");
    expect(container.className).toContain("overflow-x-auto");
  });

  it("selects a set icon when clicked", () => {
    const onSelect = vi.fn();
    render(<SetIconFilter {...defaultProps} onSelect={onSelect} />);
    const icon = screen.getByTestId("set-icon-set3");
    fireEvent.click(icon);
    expect(onSelect).toHaveBeenCalledWith("set3");
  });

  it("deselects a set icon when clicking the selected one", () => {
    const onSelect = vi.fn();
    render(<SetIconFilter {...defaultProps} selected="set3" onSelect={onSelect} />);
    const icon = screen.getByTestId("set-icon-set3");
    fireEvent.click(icon);
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("clicking 'All' button calls onSelect with null", () => {
    const onSelect = vi.fn();
    render(<SetIconFilter {...defaultProps} selected="set1" onSelect={onSelect} />);
    const container = screen.getByTestId("scroll-container");
    const allButton = container.children[0] as HTMLButtonElement;
    fireEvent.click(allButton);
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("applies selected styling to the active set icon", () => {
    render(<SetIconFilter {...defaultProps} selected="set2" />);
    const icon = screen.getByTestId("set-icon-set2");
    expect(icon.className).toContain("ring-2");
    expect(icon.className).toContain("ring-indigo-500");
  });

  it("applies selected styling to 'All' button when nothing is selected", () => {
    render(<SetIconFilter {...defaultProps} selected={null} />);
    const container = screen.getByTestId("scroll-container");
    const allButton = container.children[0] as HTMLButtonElement;
    expect(allButton.className).toContain("bg-indigo-500/20");
  });

  describe("scroll arrows", () => {
    it("does not show arrows when content does not overflow", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(3)} />);
      expect(screen.queryByTestId("scroll-left")).not.toBeInTheDocument();
      expect(screen.queryByTestId("scroll-right")).not.toBeInTheDocument();
    });

    it("shows right arrow when content overflows to the right", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
      const container = screen.getByTestId("scroll-container");
      mockScrollDimensions(container, { scrollWidth: 1000, clientWidth: 520, scrollLeft: 0 });
      fireEvent.scroll(container);
      expect(screen.getByTestId("scroll-right")).toBeInTheDocument();
      expect(screen.queryByTestId("scroll-left")).not.toBeInTheDocument();
    });

    it("shows both arrows when scrolled to the middle", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
      const container = screen.getByTestId("scroll-container");
      mockScrollDimensions(container, { scrollWidth: 1000, clientWidth: 520, scrollLeft: 200 });
      fireEvent.scroll(container);
      expect(screen.getByTestId("scroll-left")).toBeInTheDocument();
      expect(screen.getByTestId("scroll-right")).toBeInTheDocument();
    });

    it("shows only left arrow when scrolled to the end", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
      const container = screen.getByTestId("scroll-container");
      mockScrollDimensions(container, { scrollWidth: 1000, clientWidth: 520, scrollLeft: 480 });
      fireEvent.scroll(container);
      expect(screen.getByTestId("scroll-left")).toBeInTheDocument();
      expect(screen.queryByTestId("scroll-right")).not.toBeInTheDocument();
    });

    it("shows gradient fade when right arrow is visible", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
      const container = screen.getByTestId("scroll-container");
      mockScrollDimensions(container, { scrollWidth: 1000, clientWidth: 520, scrollLeft: 0 });
      fireEvent.scroll(container);
      expect(screen.getByTestId("scroll-fade")).toBeInTheDocument();
    });

    it("right arrow click calls scrollBy on the container", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
      const container = screen.getByTestId("scroll-container");
      mockScrollDimensions(container, { scrollWidth: 1000, clientWidth: 520, scrollLeft: 0 });
      fireEvent.scroll(container);

      const scrollBySpy = vi.fn();
      container.scrollBy = scrollBySpy;

      fireEvent.click(screen.getByTestId("scroll-right"));
      expect(scrollBySpy).toHaveBeenCalledWith({ left: 200, behavior: "smooth" });
    });

    it("left arrow click calls scrollBy with negative delta", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(20)} />);
      const container = screen.getByTestId("scroll-container");
      mockScrollDimensions(container, { scrollWidth: 1000, clientWidth: 520, scrollLeft: 300 });
      fireEvent.scroll(container);

      const scrollBySpy = vi.fn();
      container.scrollBy = scrollBySpy;

      fireEvent.click(screen.getByTestId("scroll-left"));
      expect(scrollBySpy).toHaveBeenCalledWith({ left: -200, behavior: "smooth" });
    });
  });

  describe("icon rendering", () => {
    it("renders img tags with scryfall URLs", () => {
      render(<SetIconFilter {...defaultProps} options={makeOptions(2)} />);
      const images = screen.getAllByRole("img");
      expect(images[0]).toHaveAttribute("src", "https://scryfall.com/sets/set1.svg");
      expect(images[1]).toHaveAttribute("src", "https://scryfall.com/sets/set2.svg");
    });

    it("shows text fallback when image fails to load", () => {
      render(<SetIconFilter {...defaultProps} options={[{ label: "Alpha", value: "lea" }]} />);
      const img = screen.getByRole("img");
      fireEvent.error(img);
      expect(screen.getByText("LEA")).toBeInTheDocument();
    });

    it("each icon button has a title attribute", () => {
      render(<SetIconFilter {...defaultProps} options={[{ label: "Alpha Edition", value: "lea" }]} />);
      const button = screen.getByTestId("set-icon-lea");
      expect(button).toHaveAttribute("title", "Alpha Edition");
    });
  });
});
