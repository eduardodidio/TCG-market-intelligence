import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Card3DTilt } from "../Card3DTilt";

vi.mock("react-parallax-tilt", () => ({
  default: ({
    children,
    className,
    ...props
  }: {
    children: React.ReactNode;
    className?: string;
    [key: string]: unknown;
  }) => (
    <div data-testid="tilt-wrapper" className={className} data-props={JSON.stringify(props)}>
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
    expect(props.glareMaxOpacity).toBe(0.15);
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
});
