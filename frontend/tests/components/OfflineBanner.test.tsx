import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { OfflineBanner } from "../../src/components/OfflineBanner";

describe("OfflineBanner", () => {
  let originalOnLine: boolean;

  beforeEach(() => {
    originalOnLine = navigator.onLine;
  });

  afterEach(() => {
    Object.defineProperty(navigator, "onLine", {
      value: originalOnLine,
      writable: true,
      configurable: true,
    });
  });

  it("does not render when online", () => {
    Object.defineProperty(navigator, "onLine", {
      value: true,
      writable: true,
      configurable: true,
    });
    render(<OfflineBanner />);
    expect(screen.queryByTestId("offline-banner")).toBeNull();
  });

  it("renders when offline", () => {
    Object.defineProperty(navigator, "onLine", {
      value: false,
      writable: true,
      configurable: true,
    });
    render(<OfflineBanner />);
    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();
    expect(screen.getByText("Offline mode -- data may be outdated")).toBeInTheDocument();
  });

  it("shows banner when going offline", () => {
    Object.defineProperty(navigator, "onLine", {
      value: true,
      writable: true,
      configurable: true,
    });
    render(<OfflineBanner />);
    expect(screen.queryByTestId("offline-banner")).toBeNull();

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });

    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();
  });

  it("hides banner when going back online", () => {
    Object.defineProperty(navigator, "onLine", {
      value: false,
      writable: true,
      configurable: true,
    });
    render(<OfflineBanner />);
    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    expect(screen.queryByTestId("offline-banner")).toBeNull();
  });

  it("has role=alert for accessibility", () => {
    Object.defineProperty(navigator, "onLine", {
      value: false,
      writable: true,
      configurable: true,
    });
    render(<OfflineBanner />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
