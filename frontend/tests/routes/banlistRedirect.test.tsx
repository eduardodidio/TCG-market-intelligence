import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const mockUser = {
  id: 1,
  email: "u@t.com",
  display_name: "T",
  avatar_url: null,
  auth_provider: "local",
  preferred_language: "en",
  is_active: true,
  is_admin: false,
  role: "user",
};

vi.mock("../../src/api/auth", () => ({
  getStoredToken: vi.fn().mockReturnValue("fake-token"),
  getStoredRefreshToken: vi.fn().mockReturnValue(null),
  clearTokens: vi.fn(),
  fetchMe: vi.fn().mockResolvedValue({ data: mockUser, meta: {}, errors: [] }),
  refreshTokens: vi.fn().mockResolvedValue({ data: null, meta: {}, errors: [] }),
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  changePassword: vi.fn(),
}));

vi.mock("../../src/api/banlist", () => ({
  fetchFormats: vi.fn().mockResolvedValue({ data: ["standard"], meta: {}, errors: [] }),
  fetchBanlistStatus: vi.fn().mockResolvedValue({ data: null, meta: {}, errors: [] }),
  fetchBanList: vi.fn().mockResolvedValue({ data: [], meta: {}, errors: [] }),
  fetchCardLegalities: vi.fn().mockResolvedValue({ data: [], meta: {}, errors: [] }),
}));

vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

async function renderAppAt(path: string) {
  window.history.pushState({}, "", path);
  const { default: App } = await import("../../src/App");
  return render(<App />);
}

describe("F177-T09: /banlist/history redirects to /banlist", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.resetModules();
  });

  it("redirects /banlist/history to the BanList page", async () => {
    await renderAppAt("/banlist/history");

    await waitFor(() => {
      expect(screen.getByTestId("page-banlist")).toBeDefined();
    });
    expect(window.location.pathname).toBe("/banlist");
  });

  it("drops query params on redirect and still renders BanList", async () => {
    await renderAppAt("/banlist/history?format=modern");

    await waitFor(() => {
      expect(screen.getByTestId("page-banlist")).toBeDefined();
    });
    expect(window.location.pathname).toBe("/banlist");
  });
});
