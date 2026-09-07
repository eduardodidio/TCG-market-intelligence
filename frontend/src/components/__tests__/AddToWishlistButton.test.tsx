import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AddToWishlistButton } from "../AddToWishlistButton";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "wishlist.addToWishlist": "Add to wishlist",
        "wishlist.removeFromWishlist": "Remove from wishlist",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock hooks
vi.mock("../../hooks/useAuth", () => ({
  useAuth: vi.fn(() => ({
    isAuthenticated: true,
    user: { id: 1 },
  })),
}));

// Mock API
vi.mock("../../api/wishlist", () => ({
  checkWishlist: vi.fn(),
  addToWishlist: vi.fn(),
  removeFromWishlist: vi.fn(),
}));

import { checkWishlist, addToWishlist } from "../../api/wishlist";
import { useAuth } from "../../hooks/useAuth";

const mockCheckWishlist = vi.mocked(checkWishlist);
const mockAddToWishlist = vi.mocked(addToWishlist);
const mockUseAuth = vi.mocked(useAuth);

describe("AddToWishlistButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { id: 1 } as any,
      error: null,
      mustChangePassword: false,
      register: vi.fn(),
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
  });

  it("renders heart button", async () => {
    mockCheckWishlist.mockResolvedValue({
      data: { wishlisted: [] },
      meta: { cursor: null, total: null, offset: null, request_id: "1" },
      errors: [],
    });

    render(<AddToWishlistButton cardId={1} />);
    expect(screen.getByTestId("wishlist-button")).toBeDefined();
  });

  it("does not render when not authenticated", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      error: null,
      mustChangePassword: false,
      register: vi.fn(),
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    const { container } = render(<AddToWishlistButton cardId={1} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows filled heart when wishlisted", async () => {
    mockCheckWishlist.mockResolvedValue({
      data: { wishlisted: [1] },
      meta: { cursor: null, total: null, offset: null, request_id: "1" },
      errors: [],
    });

    render(<AddToWishlistButton cardId={1} />);
    await waitFor(() => {
      const btn = screen.getByTestId("wishlist-button");
      expect(btn.getAttribute("title")).toBe("Remove from wishlist");
    });
  });

  it("toggles wishlist on click", async () => {
    mockCheckWishlist.mockResolvedValue({
      data: { wishlisted: [] },
      meta: { cursor: null, total: null, offset: null, request_id: "1" },
      errors: [],
    });
    mockAddToWishlist.mockResolvedValue({
      data: {} as any,
      meta: { cursor: null, total: null, offset: null, request_id: "1" },
      errors: [],
    });

    render(<AddToWishlistButton cardId={1} />);
    const btn = await screen.findByTestId("wishlist-button");
    fireEvent.click(btn);

    await waitFor(() => {
      expect(mockAddToWishlist).toHaveBeenCalledWith(1);
    });
  });
});
