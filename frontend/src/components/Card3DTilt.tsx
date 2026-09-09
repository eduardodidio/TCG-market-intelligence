import Tilt from "react-parallax-tilt";
import type { ReactNode } from "react";

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
      glareMaxOpacity={foil ? 0.15 : 0}
      glareColor="rgba(200, 180, 255, 0.3)"
      glarePosition="all"
      className={className}
    >
      {children}
    </Tilt>
  );
}
