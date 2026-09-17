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
}

export function Card3DTilt({
  children,
  disabled = false,
  foil = false,
  className,
  scale = 1.05,
  tiltMaxAngle = 12,
}: Card3DTiltProps) {
  if (disabled) {
    return <div className={className}>{children}</div>;
  }

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
      {foil ? <div className="foil-shimmer">{children}</div> : children}
    </Tilt>
  );
}
