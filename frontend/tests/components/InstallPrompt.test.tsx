import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { InstallPrompt } from "../../src/components/InstallPrompt";

// Mock useAuth
const mockAuth = { isAuthenticated: true, user: null, logout: vi.fn(), login: vi.fn() };
vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => mockAuth,
}));

describe("InstallPrompt", () => {
  let matchMediaSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    localStorage.clear();
    // Default: not standalone
    matchMediaSpy = vi.spyOn(window, "matchMedia").mockReturnValue({
      matches: false,
      media: "",
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });
    mockAuth.isAuthenticated = true;
  });

  afterEach(() => {
    matchMediaSpy.mockRestore();
  });

  it("does not render without beforeinstallprompt event", () => {
    render(<InstallPrompt />);
    expect(screen.queryByTestId("install-prompt")).toBeNull();
  });

  it("renders when beforeinstallprompt fires and user is authenticated", () => {
    render(<InstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "preventDefault", { value: vi.fn() });
      Object.defineProperty(event, "prompt", { value: vi.fn().mockResolvedValue(undefined) });
      Object.defineProperty(event, "userChoice", {
        value: Promise.resolve({ outcome: "dismissed" }),
      });
      window.dispatchEvent(event);
    });

    expect(screen.getByTestId("install-prompt")).toBeInTheDocument();
    expect(
      screen.getByText("Install TEDHC Market for a better experience"),
    ).toBeInTheDocument();
  });

  it("does not render when user is not authenticated", () => {
    mockAuth.isAuthenticated = false;
    render(<InstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "preventDefault", { value: vi.fn() });
      window.dispatchEvent(event);
    });

    expect(screen.queryByTestId("install-prompt")).toBeNull();
  });

  it("dismiss button hides the prompt and saves to localStorage", () => {
    render(<InstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "preventDefault", { value: vi.fn() });
      window.dispatchEvent(event);
    });

    expect(screen.getByTestId("install-prompt")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("install-prompt-dismiss"));
    expect(screen.queryByTestId("install-prompt")).toBeNull();
    expect(localStorage.getItem("tcg_install_dismissed_at")).toBeTruthy();
  });

  it("does not render when dismissed recently", () => {
    localStorage.setItem("tcg_install_dismissed_at", String(Date.now()));
    render(<InstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "preventDefault", { value: vi.fn() });
      window.dispatchEvent(event);
    });

    expect(screen.queryByTestId("install-prompt")).toBeNull();
  });

  it("does not render in standalone mode", () => {
    matchMediaSpy.mockReturnValue({
      matches: true,
      media: "(display-mode: standalone)",
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });

    render(<InstallPrompt />);

    act(() => {
      const event = new Event("beforeinstallprompt");
      Object.defineProperty(event, "preventDefault", { value: vi.fn() });
      window.dispatchEvent(event);
    });

    expect(screen.queryByTestId("install-prompt")).toBeNull();
  });
});
