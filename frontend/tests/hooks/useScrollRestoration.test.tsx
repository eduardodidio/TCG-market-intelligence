import { describe, it, expect, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useScrollRestoration } from "../../src/hooks/useScrollRestoration";

function TestComponent({ routeKey }: { routeKey?: string }) {
  useScrollRestoration(routeKey);
  return <div data-testid="test">test</div>;
}

describe("useScrollRestoration", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("saves scroll position to sessionStorage on unmount", () => {
    // Mock scrollY
    Object.defineProperty(window, "scrollY", { value: 500, writable: true });

    const { unmount } = render(
      <MemoryRouter initialEntries={["/collection"]}>
        <TestComponent routeKey="collection" />
      </MemoryRouter>,
    );

    unmount();

    const saved = sessionStorage.getItem("scroll_collection");
    expect(saved).toBe("500");
  });

  it("stores scroll position with correct key format", () => {
    Object.defineProperty(window, "scrollY", { value: 300, writable: true });

    const { unmount } = render(
      <MemoryRouter initialEntries={["/cards"]}>
        <TestComponent routeKey="cards" />
      </MemoryRouter>,
    );

    unmount();

    expect(sessionStorage.getItem("scroll_cards")).toBe("300");
  });

  it("does not save zero scroll position", () => {
    Object.defineProperty(window, "scrollY", { value: 0, writable: true });

    const { unmount } = render(
      <MemoryRouter initialEntries={["/test"]}>
        <TestComponent routeKey="test" />
      </MemoryRouter>,
    );

    unmount();

    expect(sessionStorage.getItem("scroll_test")).toBeNull();
  });
});
