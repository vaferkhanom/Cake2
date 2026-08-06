/**
 * Custom animated icon set — NO raw system emoji.
 * Consistent 2px stroke, rounded caps, pastel palette.
 * Each icon is a component; animate with Framer Motion where needed.
 */

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function PlusIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function BackIcon({ size = 24, className }: IconProps) {
  // RTL: "back" points right
  return (
    <svg {...base(size)} className={className}>
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

export function CheckIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M4 12.5l5 5L20 6.5" />
    </svg>
  );
}

export function CloseIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function SparkleIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" />
    </svg>
  );
}

export function HeartIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 20s-7-4.5-9-9c-1.2-2.8.8-6 4-6 2 0 3.5 1 4.5 2.5h1C13.5 6 15 5 17 5c3.2 0 5.2 3.2 4 6-2 4.5-9 9-9 9z" />
    </svg>
  );
}

export function ListIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M4 6h16M4 12h16M4 18h10" />
    </svg>
  );
}

export function UserIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5" />
    </svg>
  );
}

export function ClockIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </svg>
  );
}

export function FlameIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 3c1 3-4 5-4 9a4 4 0 008 0c0-2-1-3-2-4-1 1-2 2-2 3-1-2 0-5 0-8z" />
    </svg>
  );
}

export function BrokenHeartIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 20s-7-4.5-9-9c-1.2-2.8.8-6 4-6 2 0 3.5 1 4.5 2.5L12 12l1-1" />
      <path d="M20 3l-7 7M15 5l6 6" />
    </svg>
  );
}

export function AlertIcon({ size = 24, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 3L2.5 20h19L12 3z" />
      <path d="M12 10v4M12 17.5v.5" />
    </svg>
  );
}
