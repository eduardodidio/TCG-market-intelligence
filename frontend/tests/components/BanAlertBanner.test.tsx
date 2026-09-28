import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BanAlertBanner } from "../../src/components/BanAlertBanner";

describe("BanAlertBanner", () => {
  it("renders when bannedCount > 0", () => {
    render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={3}
          restrictedCount={0}
          recentlyChangedCount={0}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("ban-alert-banner")).toBeInTheDocument();
    expect(screen.getByText(/3/)).toBeInTheDocument();
  });

  it("renders when restrictedCount > 0", () => {
    render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={0}
          restrictedCount={2}
          recentlyChangedCount={0}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("ban-alert-banner")).toBeInTheDocument();
  });

  it("hidden when both counts are 0", () => {
    const { container } = render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={0}
          restrictedCount={0}
          recentlyChangedCount={0}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    expect(container.innerHTML).toBe("");
  });

  it("dismiss button calls onDismiss", () => {
    const onDismiss = vi.fn();
    render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={1}
          restrictedCount={0}
          recentlyChangedCount={0}
          onDismiss={onDismiss}
        />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByTestId("ban-alert-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("shows recently changed text when count > 0", () => {
    render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={1}
          restrictedCount={0}
          recentlyChangedCount={5}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });

  it("uses red styling when banned", () => {
    render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={1}
          restrictedCount={0}
          recentlyChangedCount={0}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    const banner = screen.getByTestId("ban-alert-banner");
    expect(banner.className).toContain("bg-red-900");
  });

  it("uses amber styling when only restricted", () => {
    render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={0}
          restrictedCount={2}
          recentlyChangedCount={0}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    const banner = screen.getByTestId("ban-alert-banner");
    expect(banner.className).toContain("bg-amber-900");
  });

  it("renders link to banlist when banned cards exist", () => {
    render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={3}
          restrictedCount={0}
          recentlyChangedCount={0}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    const link = screen.getByTestId("ban-alert-link");
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/banlist?owned=1");
  });

  it("does not render link when both counts are 0", () => {
    const { container } = render(
      <MemoryRouter>
        <BanAlertBanner
          bannedCount={0}
          restrictedCount={0}
          recentlyChangedCount={0}
          onDismiss={() => {}}
        />
      </MemoryRouter>,
    );
    expect(container.innerHTML).toBe("");
  });
});
