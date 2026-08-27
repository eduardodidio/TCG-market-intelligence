import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TreasureBalance } from "../../src/components/TreasureBalance";
import { Layout } from "../../src/components/Layout";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";
import { CurrencyProvider } from "../../src/contexts/CurrencyContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";

// Mock useCredits hook
const mockClaimBonus = vi.fn().mockResolvedValue(undefined);
const mockRefetch = vi.fn();

let mockCreditsState = {
  balance: 25,
  bonusEligible: false,
  nextBonusAt: null as string | null,
  isAdmin: false,
  loading: false,
  refetch: mockRefetch,
  claimBonus: mockClaimBonus,
};

vi.mock("../../src/hooks/useCredits", () => ({
  useCredits: () => mockCreditsState,
}));

// Mock localStorage
beforeEach(() => {
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue(null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
  mockCreditsState = {
    balance: 25,
    bonusEligible: false,
    nextBonusAt: null,
    isAdmin: false,
    loading: false,
    refetch: mockRefetch,
    claimBonus: mockClaimBonus,
  };
  mockClaimBonus.mockClear();
  mockRefetch.mockClear();
});

function renderTreasureBalance() {
  return render(
    <LanguageProvider>
      <TreasureBalance />
    </LanguageProvider>,
  );
}

const mockAuthAuthenticated: AuthContextValue = {
  user: {
    id: 1,
    email: "test@example.com",
    display_name: "Test User",
    avatar_url: null,
    auth_provider: "email",
    preferred_language: null,
    is_active: true,
    is_admin: false,
  },
  loading: false,
  error: null,
  isAuthenticated: true,
  login: vi.fn().mockResolvedValue(null),
  register: vi.fn().mockResolvedValue(null),
  logout: vi.fn().mockResolvedValue(undefined),
  mustChangePassword: false,
  changePassword: vi.fn().mockResolvedValue(null),
};

const mockAuthUnauthenticated: AuthContextValue = {
  user: null,
  loading: false,
  error: null,
  isAuthenticated: false,
  login: vi.fn().mockResolvedValue(null),
  register: vi.fn().mockResolvedValue(null),
  logout: vi.fn().mockResolvedValue(undefined),
  mustChangePassword: false,
  changePassword: vi.fn().mockResolvedValue(null),
};

function renderLayout(auth: AuthContextValue = mockAuthAuthenticated) {
  return render(
    <LanguageProvider>
      <AuthContext.Provider value={auth}>
        <CurrencyProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Layout />
          </MemoryRouter>
        </CurrencyProvider>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("TreasureBalance", () => {
  it("renders balance number and token icon", () => {
    renderTreasureBalance();

    const icon = screen.getByTestId("treasure-icon");
    expect(icon).toBeDefined();
    expect(icon.tagName).toBe("IMG");

    const value = screen.getByTestId("treasure-balance-value");
    expect(value.textContent).toBe("25");
  });

  it("renders the label text", () => {
    renderTreasureBalance();

    expect(screen.getByText("Treasure Tokens")).toBeDefined();
  });

  it("shows claim button when bonusEligible is true", () => {
    mockCreditsState.bonusEligible = true;
    renderTreasureBalance();

    const claimBtn = screen.getByTestId("claim-bonus-button");
    expect(claimBtn).toBeDefined();
    expect(claimBtn.textContent).toBe("Claim Bonus");
  });

  it("hides claim button when bonusEligible is false", () => {
    mockCreditsState.bonusEligible = false;
    renderTreasureBalance();

    expect(screen.queryByTestId("claim-bonus-button")).toBeNull();
  });

  it("shows admin badge when isAdmin is true", () => {
    mockCreditsState.isAdmin = true;
    renderTreasureBalance();

    const badge = screen.getByTestId("admin-badge");
    expect(badge).toBeDefined();
    expect(badge.textContent).toBe("Admin");
  });

  it("hides admin badge when isAdmin is false", () => {
    mockCreditsState.isAdmin = false;
    renderTreasureBalance();

    expect(screen.queryByTestId("admin-badge")).toBeNull();
  });

  it("calls claimBonus when claim button is clicked", async () => {
    mockCreditsState.bonusEligible = true;
    renderTreasureBalance();

    const claimBtn = screen.getByTestId("claim-bonus-button");
    fireEvent.click(claimBtn);

    await waitFor(() => {
      expect(mockClaimBonus).toHaveBeenCalledTimes(1);
    });
  });

  it("shows loading skeleton when loading with null balance", () => {
    mockCreditsState.loading = true;
    mockCreditsState.balance = null as unknown as number;
    renderTreasureBalance();

    const container = screen.getByTestId("treasure-balance");
    expect(container).toBeDefined();
    // Should show "..." text for loading
    expect(container.textContent).toContain("...");
  });

  it("displays fallback when balance is null", () => {
    mockCreditsState.loading = false;
    mockCreditsState.balance = null as unknown as number;
    renderTreasureBalance();

    const value = screen.getByTestId("treasure-balance-value");
    expect(value.textContent).toBe("...");
  });

  it("shows balance of zero correctly", () => {
    mockCreditsState.balance = 0;
    renderTreasureBalance();

    const value = screen.getByTestId("treasure-balance-value");
    expect(value.textContent).toBe("0");
  });

  it("treasure image is rectangular (not circular)", () => {
    renderTreasureBalance();

    const icon = screen.getByTestId("treasure-icon");
    const classes = icon.className;
    expect(classes).not.toContain("rounded-full");
    expect(classes).toContain("rounded");
  });

  it("opens modal when treasure image is clicked", () => {
    renderTreasureBalance();

    expect(screen.queryByTestId("treasure-modal-backdrop")).toBeNull();

    const icon = screen.getByTestId("treasure-icon");
    fireEvent.click(icon);

    expect(screen.getByTestId("treasure-modal-backdrop")).toBeDefined();
  });

  it("modal receives correct count from balance", () => {
    mockCreditsState.balance = 42;
    renderTreasureBalance();

    const icon = screen.getByTestId("treasure-icon");
    fireEvent.click(icon);

    const count = screen.getByTestId("treasure-modal-count");
    expect(count.textContent).toBe("42");
  });

  it("modal closes when backdrop is clicked (after exit animation)", () => {
    vi.useFakeTimers();
    renderTreasureBalance();

    const icon = screen.getByTestId("treasure-icon");
    fireEvent.click(icon);
    expect(screen.getByTestId("treasure-modal-backdrop")).toBeDefined();

    const backdrop = screen.getByTestId("treasure-modal-backdrop");
    fireEvent.click(backdrop);

    // Modal still present during exit animation
    expect(screen.queryByTestId("treasure-modal-backdrop")).not.toBeNull();
    act(() => { vi.advanceTimersByTime(600); });
    expect(screen.queryByTestId("treasure-modal-backdrop")).toBeNull();
    vi.useRealTimers();
  });
});

describe("TreasureBalance in Layout", () => {
  it("shows TreasureBalance when authenticated", () => {
    renderLayout(mockAuthAuthenticated);

    const section = screen.getByTestId("treasure-balance-section");
    expect(section).toBeDefined();

    const balance = screen.getByTestId("treasure-balance");
    expect(balance).toBeDefined();
  });

  it("hides TreasureBalance when not authenticated", () => {
    renderLayout(mockAuthUnauthenticated);

    expect(screen.queryByTestId("treasure-balance-section")).toBeNull();
  });
});
