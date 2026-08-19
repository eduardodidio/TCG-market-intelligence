import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Pagination } from "../../src/components/Pagination";

describe("Pagination", () => {
  it("renders 'Load more' button when cursor is not null", () => {
    render(<Pagination cursor="abc123" onLoadMore={() => {}} loading={false} />);
    expect(screen.getByTestId("load-more-button")).toBeDefined();
    expect(screen.getByText("Load more")).toBeDefined();
  });

  it("renders nothing when cursor is null", () => {
    const { container } = render(
      <Pagination cursor={null} onLoadMore={() => {}} loading={false} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("fires onLoadMore when button is clicked", () => {
    const handleLoadMore = vi.fn();
    render(<Pagination cursor="abc123" onLoadMore={handleLoadMore} loading={false} />);
    fireEvent.click(screen.getByTestId("load-more-button"));
    expect(handleLoadMore).toHaveBeenCalledOnce();
  });

  it("shows 'Loading...' text when loading is true", () => {
    render(<Pagination cursor="abc123" onLoadMore={() => {}} loading={true} />);
    expect(screen.getByText("Loading...")).toBeDefined();
  });

  it("disables button when loading", () => {
    render(<Pagination cursor="abc123" onLoadMore={() => {}} loading={true} />);
    const button = screen.getByTestId("load-more-button") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("button is enabled when not loading", () => {
    render(<Pagination cursor="abc123" onLoadMore={() => {}} loading={false} />);
    const button = screen.getByTestId("load-more-button") as HTMLButtonElement;
    expect(button.disabled).toBe(false);
  });
});
