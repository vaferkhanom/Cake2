/**
 * Framer Motion tokens — ONE central file, imported everywhere.
 * The "iOS smooth" recipe from the spec. Never hand-roll per-component values.
 */

export const durations = { instant: 100, fast: 200, normal: 300, slow: 450 };

export const easings = {
  /** navigation */
  standard: [0.25, 0.1, 0.25, 1] as const,
  /** entrances */
  easeOut: [0, 0, 0.58, 1] as const,
  /** exits */
  easeIn: [0.42, 0, 1, 1] as const,
};

export const spring = { type: "spring", stiffness: 300, damping: 24 } as const;
export const gentleSpring = {
  type: "spring",
  stiffness: 220,
  damping: 26,
} as const;

/** Card entrance: fade + translateY 12→0, 200ms easeOut */
export const cardEntrance = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 8 },
  transition: { duration: durations.fast / 1000, ease: easings.easeOut },
} as const;

/** Tap: scale 0.96 @100ms */
export const tapScale = { whileTap: { scale: 0.96 } } as const;

/** DONE celebration: scale pop [0,1.15,1] ~450ms spring */
export const donePop = {
  initial: { scale: 0 },
  animate: { scale: [0, 1.15, 1] },
  transition: { ...spring, duration: 0.45 },
} as const;

/** BROKEN/DISPUTED: gentle shake [0,-4,4,-4,0] 300ms */
export const gentleShake = {
  animate: { x: [0, -4, 4, -4, 0] },
  transition: { duration: 0.3 },
} as const;

/** Score/streak count-up ~600ms spring-driven */
export const countUpSpring = {
  ...spring,
  duration: 0.6,
} as const;
