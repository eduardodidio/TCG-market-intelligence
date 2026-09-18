import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { Card3DTilt } from "../Card3DTilt";

vi.mock("react-parallax-tilt", () => ({
  default: ({
    children,
    className,
    style,
    ...props
  }: {
    children: React.ReactNode;
    className?: string;
    style?: React.CSSProperties;
    [key: string]: unknown;
  }) => (
    <div data-testid="tilt-wrapper" className={className} style={style} data-props={JSON.stringify(props)}>
      {children}
    </div>
  ),
}));

describe("Card3DTilt", () => {
  it("renders children correctly", () => {
    render(
      <Card3DTilt>
        <img alt="card" src="/test.png" />
      </Card3DTilt>,
    );
    expect(screen.getByAltText("card")).toBeInTheDocument();
  });

  it("renders a plain div when disabled", () => {
    render(
      <Card3DTilt disabled>
        <span>content</span>
      </Card3DTilt>,
    );
    expect(screen.queryByTestId("tilt-wrapper")).not.toBeInTheDocument();
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  it("renders Tilt wrapper when not disabled", () => {
    render(
      <Card3DTilt>
        <span>content</span>
      </Card3DTilt>,
    );
    expect(screen.getByTestId("tilt-wrapper")).toBeInTheDocument();
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  it("enables glare when foil is true", () => {
    render(
      <Card3DTilt foil>
        <span>foil card</span>
      </Card3DTilt>,
    );
    const wrapper = screen.getByTestId("tilt-wrapper");
    const props = JSON.parse(wrapper.getAttribute("data-props") || "{}");
    expect(props.glareEnable).toBe(true);
    expect(props.glareMaxOpacity).toBe(0.35);
  });

  it("disables glare when foil is false", () => {
    render(
      <Card3DTilt>
        <span>normal card</span>
      </Card3DTilt>,
    );
    const wrapper = screen.getByTestId("tilt-wrapper");
    const props = JSON.parse(wrapper.getAttribute("data-props") || "{}");
    expect(props.glareEnable).toBe(false);
    expect(props.glareMaxOpacity).toBe(0);
  });

  it("passes className to container", () => {
    render(
      <Card3DTilt className="custom-class">
        <span>content</span>
      </Card3DTilt>,
    );
    const wrapper = screen.getByTestId("tilt-wrapper");
    expect(wrapper).toHaveClass("custom-class");
  });

  it("passes className to plain div when disabled", () => {
    render(
      <Card3DTilt disabled className="custom-class">
        <span>content</span>
      </Card3DTilt>,
    );
    const container = screen.getByText("content").parentElement;
    expect(container).toHaveClass("custom-class");
  });

  it("uses custom scale and tiltMaxAngle", () => {
    render(
      <Card3DTilt scale={1.1} tiltMaxAngle={20}>
        <span>content</span>
      </Card3DTilt>,
    );
    const wrapper = screen.getByTestId("tilt-wrapper");
    const props = JSON.parse(wrapper.getAttribute("data-props") || "{}");
    expect(props.scale).toBe(1.1);
    expect(props.tiltMaxAngleX).toBe(20);
    expect(props.tiltMaxAngleY).toBe(20);
  });

  it("uses default scale and tiltMaxAngle", () => {
    render(
      <Card3DTilt>
        <span>content</span>
      </Card3DTilt>,
    );
    const wrapper = screen.getByTestId("tilt-wrapper");
    const props = JSON.parse(wrapper.getAttribute("data-props") || "{}");
    expect(props.scale).toBe(1.05);
    expect(props.tiltMaxAngleX).toBe(12);
    expect(props.tiltMaxAngleY).toBe(12);
  });

  it("adds foil-shimmer class when foil is true", () => {
    render(
      <Card3DTilt foil>
        <span>foil card</span>
      </Card3DTilt>,
    );
    const shimmerDiv = screen.getByText("foil card").parentElement;
    expect(shimmerDiv).toHaveClass("foil-shimmer");
  });

  it("does NOT add foil-shimmer class when foil is false", () => {
    render(
      <Card3DTilt>
        <span>normal card</span>
      </Card3DTilt>,
    );
    const parent = screen.getByText("normal card").parentElement;
    expect(parent).not.toHaveClass("foil-shimmer");
  });

  it("glareMaxOpacity is higher when foil=true vs foil=false", () => {
    const { unmount } = render(
      <Card3DTilt foil>
        <span>foil</span>
      </Card3DTilt>,
    );
    const foilWrapper = screen.getByTestId("tilt-wrapper");
    const foilProps = JSON.parse(foilWrapper.getAttribute("data-props") || "{}");
    const foilOpacity = foilProps.glareMaxOpacity;
    unmount();

    render(
      <Card3DTilt>
        <span>non-foil</span>
      </Card3DTilt>,
    );
    const normalWrapper = screen.getByTestId("tilt-wrapper");
    const normalProps = JSON.parse(normalWrapper.getAttribute("data-props") || "{}");
    const normalOpacity = normalProps.glareMaxOpacity;

    expect(foilOpacity).toBeGreaterThan(normalOpacity);
    expect(foilOpacity).toBeGreaterThanOrEqual(0.35);
    expect(normalOpacity).toBe(0);
  });

  it("renders Tilt wrapper with overflow hidden and borderRadius style", () => {
    render(
      <Card3DTilt>
        <span>content</span>
      </Card3DTilt>,
    );
    const wrapper = screen.getByTestId("tilt-wrapper");
    expect(wrapper.style.overflow).toBe("hidden");
    expect(wrapper.style.borderRadius).toBe("12px");
  });

  it("does not apply overflow/borderRadius style when disabled", () => {
    render(
      <Card3DTilt disabled>
        <span>content</span>
      </Card3DTilt>,
    );
    expect(screen.queryByTestId("tilt-wrapper")).not.toBeInTheDocument();
    const container = screen.getByText("content").parentElement;
    expect(container?.style.overflow).toBeFalsy();
    expect(container?.style.borderRadius).toBeFalsy();
  });

  it("uses holographic white glare color for foil cards", () => {
    render(
      <Card3DTilt foil>
        <span>foil card</span>
      </Card3DTilt>,
    );
    const wrapper = screen.getByTestId("tilt-wrapper");
    const props = JSON.parse(wrapper.getAttribute("data-props") || "{}");
    expect(props.glareColor).toBe("rgba(255, 255, 255, 0.4)");
  });

  it("renders foil-shimmer-wrapper with data-testid when foil=true", () => {
    render(
      <Card3DTilt foil>
        <span>foil card</span>
      </Card3DTilt>,
    );
    expect(screen.getByTestId("foil-shimmer-wrapper")).toBeInTheDocument();
  });

  it("does NOT render foil-shimmer-wrapper when foil=false", () => {
    render(
      <Card3DTilt>
        <span>normal card</span>
      </Card3DTilt>,
    );
    expect(screen.queryByTestId("foil-shimmer-wrapper")).not.toBeInTheDocument();
  });

  it("adds foil-shimmer--glow class when glowBorder=true and foil=true", () => {
    render(
      <Card3DTilt foil glowBorder>
        <span>glow card</span>
      </Card3DTilt>,
    );
    const shimmerWrapper = screen.getByTestId("foil-shimmer-wrapper");
    expect(shimmerWrapper).toHaveClass("foil-shimmer--glow");
  });

  it("does NOT add foil-shimmer--glow class when glowBorder=false", () => {
    render(
      <Card3DTilt foil>
        <span>no glow</span>
      </Card3DTilt>,
    );
    const shimmerWrapper = screen.getByTestId("foil-shimmer-wrapper");
    expect(shimmerWrapper).not.toHaveClass("foil-shimmer--glow");
  });

  describe("mouse interaction (foil=true)", () => {
    beforeEach(() => {
      vi.spyOn(window, "matchMedia").mockReturnValue({
        matches: false,
        media: "",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      } as MediaQueryList);
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it("adds foil-shimmer--interactive class on mouse enter", () => {
      render(
        <Card3DTilt foil>
          <span>foil card</span>
        </Card3DTilt>,
      );
      const shimmerWrapper = screen.getByTestId("foil-shimmer-wrapper");
      fireEvent.mouseEnter(shimmerWrapper);
      expect(shimmerWrapper).toHaveClass("foil-shimmer--interactive");
    });

    it("removes foil-shimmer--interactive class on mouse leave", () => {
      render(
        <Card3DTilt foil>
          <span>foil card</span>
        </Card3DTilt>,
      );
      const shimmerWrapper = screen.getByTestId("foil-shimmer-wrapper");
      fireEvent.mouseEnter(shimmerWrapper);
      expect(shimmerWrapper).toHaveClass("foil-shimmer--interactive");
      fireEvent.mouseLeave(shimmerWrapper);
      expect(shimmerWrapper).not.toHaveClass("foil-shimmer--interactive");
    });

    it("sets --mouse-x and --mouse-y CSS variables on mouse move", () => {
      render(
        <Card3DTilt foil>
          <span>foil card</span>
        </Card3DTilt>,
      );
      const shimmerWrapper = screen.getByTestId("foil-shimmer-wrapper");

      // Mock getBoundingClientRect
      vi.spyOn(shimmerWrapper, "getBoundingClientRect").mockReturnValue({
        left: 0,
        top: 0,
        width: 200,
        height: 300,
        right: 200,
        bottom: 300,
        x: 0,
        y: 0,
        toJSON: vi.fn(),
      });

      fireEvent.mouseMove(shimmerWrapper, { clientX: 100, clientY: 150 });

      expect(shimmerWrapper.style.getPropertyValue("--mouse-x")).toBe("0.500");
      expect(shimmerWrapper.style.getPropertyValue("--mouse-y")).toBe("0.500");
    });
  });

  describe("prefers-reduced-motion", () => {
    beforeEach(() => {
      vi.spyOn(window, "matchMedia").mockReturnValue({
        matches: true,
        media: "(prefers-reduced-motion: reduce)",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      } as MediaQueryList);
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it("does NOT add foil-shimmer--interactive class on mouse enter when reduced motion is preferred", () => {
      render(
        <Card3DTilt foil>
          <span>foil card</span>
        </Card3DTilt>,
      );
      const shimmerWrapper = screen.getByTestId("foil-shimmer-wrapper");
      fireEvent.mouseEnter(shimmerWrapper);
      expect(shimmerWrapper).not.toHaveClass("foil-shimmer--interactive");
    });

    it("does NOT set CSS variables on mouse move when reduced motion is preferred", () => {
      render(
        <Card3DTilt foil>
          <span>foil card</span>
        </Card3DTilt>,
      );
      const shimmerWrapper = screen.getByTestId("foil-shimmer-wrapper");

      vi.spyOn(shimmerWrapper, "getBoundingClientRect").mockReturnValue({
        left: 0,
        top: 0,
        width: 200,
        height: 300,
        right: 200,
        bottom: 300,
        x: 0,
        y: 0,
        toJSON: vi.fn(),
      });

      fireEvent.mouseMove(shimmerWrapper, { clientX: 100, clientY: 150 });

      // Default values from CSS, not from JS handler
      expect(shimmerWrapper.style.getPropertyValue("--mouse-x")).toBe("");
    });
  });
});
