import { useEffect, useRef } from "react";
import Tilt from "react-parallax-tilt";
import type { ReactNode } from "react";
import "../styles/foil-shimmer.css";

interface Card3DTiltProps {
  children: ReactNode;
  disabled?: boolean;
  foil?: boolean;
  className?: string;
  scale?: number;
  tiltMaxAngle?: number;
  /** When true, adds the foil-shimmer--glow class for rainbow border glow */
  glowBorder?: boolean;
}

export function Card3DTilt({
  children,
  disabled = false,
  foil = false,
  className,
  scale = 1.05,
  tiltMaxAngle = 12,
  glowBorder = false,
}: Card3DTiltProps) {
  const shimmerRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useRef(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia) {
      prefersReducedMotion.current = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
    }
  }, []);

  if (disabled) {
    return <div className={className}>{children}</div>;
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion.current || !foil) return;
    const el = shimmerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    el.style.setProperty("--mouse-x", x.toFixed(3));
    el.style.setProperty("--mouse-y", y.toFixed(3));
  };

  const handleMouseEnter = () => {
    if (prefersReducedMotion.current || !foil) return;
    shimmerRef.current?.classList.add("foil-shimmer--interactive");
  };

  const handleMouseLeave = () => {
    if (!foil) return;
    shimmerRef.current?.classList.remove("foil-shimmer--interactive");
  };

  const shimmerClasses = [
    "foil-shimmer",
    glowBorder ? "foil-shimmer--glow" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Tilt
      tiltMaxAngleX={tiltMaxAngle}
      tiltMaxAngleY={tiltMaxAngle}
      scale={scale}
      perspective={1000}
      transitionSpeed={300}
      glareEnable={foil}
      glareMaxOpacity={foil ? 0.35 : 0}
      glareColor="rgba(255, 255, 255, 0.4)"
      glarePosition="all"
      className={className}
      style={{ borderRadius: '12px', overflow: 'hidden' }}
    >
      {foil ? (
        <div
          ref={shimmerRef}
          className={shimmerClasses}
          onMouseMove={handleMouseMove}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          data-testid="foil-shimmer-wrapper"
        >
          {children}
        </div>
      ) : (
        children
      )}
    </Tilt>
  );
}
