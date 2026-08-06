import { motion } from "framer-motion";
import { cardEntrance, durations } from "../motion/presets";

/**
 * Animated count-up for score/streak — spring-driven, ~600ms.
 */
export default function CountUp({ value, className }: { value: number; className?: string }) {
  return (
    <motion.span
      className={className}
      initial={{ opacity: 0.4, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        duration: durations.slow / 1000,
        type: "spring",
        stiffness: 200,
        damping: 20,
      }}
      key={value}
    >
      {value}
    </motion.span>
  );
}

/** Card with the standard entrance + tap feedback */
export function Card({
  children,
  onClick,
  className = "",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  const Tag = onClick ? motion.div : motion.div;
  return (
    <Tag
      {...cardEntrance}
      whileTap={onClick ? { scale: 0.96 } : undefined}
      onClick={onClick}
      className={`rounded-card bg-card p-4 shadow-card dark:bg-card-dark dark:shadow-cardDark ${className}`}
    >
      {children}
    </Tag>
  );
}
