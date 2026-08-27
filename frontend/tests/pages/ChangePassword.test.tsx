import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ChangePassword } from "../../src/pages/ChangePassword";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function createAuthValue(overrides?: Partial<AuthContextValue>): AuthContextValue {
  return {
    user: null,
    loading: false,
    error: null,
    isAuthenticated: false,
    mustChangePassword: true,
    login: vi.fn().mockResolvedValue(null),
    register: vi.fn().mockResolvedValue(null),
    logout: vi.fn(),
    changePassword: vi.fn().mockResolvedValue(null),
    ...overrides,
  };
}

function renderPage(authOverrides?: Partial<AuthContextValue>) {
  const authValue = createAuthValue(authOverrides);
  return {
    authValue,
    ...render(
      <AuthContext.Provider value={authValue}>
        <MemoryRouter>
          <ChangePassword />
        </MemoryRouter>
      </AuthContext.Provider>,
    ),
  };
}

describe("ChangePassword", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it("renders form fields", () => {
    renderPage();
    expect(screen.getByTestId("page-change-password")).toBeInTheDocument();
    expect(screen.getByTestId("current-password-input")).toBeInTheDocument();
    expect(screen.getByTestId("new-password-input")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-password-input")).toBeInTheDocument();
    expect(screen.getByTestId("change-password-submit")).toBeInTheDocument();
  });

  it("shows password expired warning", () => {
    renderPage();
    // The amber warning box with passwordExpiredMessage
    expect(screen.getByText(/password.*expired/i)).toBeInTheDocument();
  });

  it("validates password match", async () => {
    renderPage();

    fireEvent.change(screen.getByTestId("current-password-input"), {
      target: { value: "oldpassword" },
    });
    fireEvent.change(screen.getByTestId("new-password-input"), {
      target: { value: "newpassword1" },
    });
    fireEvent.change(screen.getByTestId("confirm-password-input"), {
      target: { value: "differentpass" },
    });
    fireEvent.click(screen.getByTestId("change-password-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("change-password-error")).toBeInTheDocument();
    });
  });

  it("submits and redirects on success", async () => {
    const changePassword = vi.fn().mockResolvedValue(null);
    renderPage({ changePassword });

    fireEvent.change(screen.getByTestId("current-password-input"), {
      target: { value: "oldpassword" },
    });
    fireEvent.change(screen.getByTestId("new-password-input"), {
      target: { value: "newstrongpass" },
    });
    fireEvent.change(screen.getByTestId("confirm-password-input"), {
      target: { value: "newstrongpass" },
    });
    fireEvent.click(screen.getByTestId("change-password-submit"));

    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledWith("oldpassword", "newstrongpass");
      expect(mockNavigate).toHaveBeenCalledWith("/collection", { replace: true });
    });
  });

  it("shows error from changePassword", async () => {
    const changePassword = vi.fn().mockResolvedValue("Current password is incorrect");
    renderPage({ changePassword });

    fireEvent.change(screen.getByTestId("current-password-input"), {
      target: { value: "wrongpass" },
    });
    fireEvent.change(screen.getByTestId("new-password-input"), {
      target: { value: "newstrongpass" },
    });
    fireEvent.change(screen.getByTestId("confirm-password-input"), {
      target: { value: "newstrongpass" },
    });
    fireEvent.click(screen.getByTestId("change-password-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("change-password-error")).toBeInTheDocument();
      expect(screen.getByText("Current password is incorrect")).toBeInTheDocument();
    });
  });
});
