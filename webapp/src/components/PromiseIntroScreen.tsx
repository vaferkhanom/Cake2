/**
 * PromiseIntroScreen — Wooden plank intro screen.
 *
 * Shows once per session before the Dashboard. A wooden sign hanging
 * from two chains drops down from the top over ~3.5 seconds, displaying
 * a random cute Persian quote about promises. Once landed, the plank
 * becomes tappable to enter the app.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

// Persian quotes about promises — cute, warm, playful
const QUOTES = [
  "قول بده، قلب ببر! 💕",
  "زیر قولت نزن، عزیزم! 😤",
  "قولت = طلایت ✨",
  "یه قول خوب، یه قدم بزرگ 🚀",
  "قول بده و عمل کن، قهرمان شو! 🦸",
  "قولت رو نگه دار، دلت آرومه 🌸",
  "قول بدون عمل مثل کیک بدون خامه 🎂",
  "قول بده، لبخند بزن! 😊",
  "قولت یه قرار مقدسه 🤝",
  "قول بده و ثابتقدم باش 💪",
  "قولت رو جدی بگیر، بقیه هم جدی می‌گیرن 👀",
  "یه قول کوچیک، یه تغییر بزرگ 🌟",
  "قول بده که فردا بهتر باشی! 🌅",
  "قولت رو بنویس، عملش کن، غرور کن! 📝",
  "قول بی‌عمل؟ نه مرسی! 🙅",
  "قول بده و شجاع باش 🦁",
  "قولت = شخصیتت 🪞",
  "قول بده، دنیا قشنگ‌تر می‌شه 🌈",
  "هر قولی یه شروع تازه‌ست 🌱",
  "قول بده و لذت ببر از عمل کردنش! 🎉",
  "قولت رو محکم نگه دار، مثل یه ستاره ⭐",
  "قول دادی؟ پس اجراش کن! 🎬",
  "قول مثل یه بذر می‌مونه، آبش بده! 🌻",
  "قول بده و پیشرفت کن، قدم به قدم 🪜",
];

// sessionStorage key for one-shot-per-session
const INTRO_SHOWN_KEY = "promise-intro-shown";

export function shouldShowIntro(): boolean {
  try {
    return !sessionStorage.getItem(INTRO_SHOWN_KEY);
  } catch {
    return true;
  }
}

export function markIntroShown(): void {
  try {
    sessionStorage.setItem(INTRO_SHOWN_KEY, "1");
  } catch {
    // ignore
  }
}

export default function PromiseIntroScreen({ onDone }: { onDone: () => void }) {
  const [canTap, setCanTap] = useState(false);

  const quote = useMemo(() => QUOTES[Math.floor(Math.random() * QUOTES.length)], []);

  // After drop animation completes (~3.5s), enable tapping
  useEffect(() => {
    const timer = setTimeout(() => setCanTap(true), 3600);
    return () => clearTimeout(timer);
  }, []);

  const handleTap = useCallback(() => {
    if (!canTap) return;
    markIntroShown();
    onDone();
  }, [canTap, onDone]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={handleTap}
      style={{ pointerEvents: canTap ? "auto" : "none" }}
    >
      {/* The plank + chains — drops from top */}
      <motion.div
        initial={{ y: "-120vh" }}
        animate={{ y: 0 }}
        transition={{
          type: "spring",
          damping: 18,
          stiffness: 40,
          duration: 3.5,
        }}
        className="relative flex flex-col items-center"
        style={{ pointerEvents: "none" }}
      >
        {/* Chains */}
        <div className="flex justify-between" style={{ width: "220px" }}>
          {/* Left chain */}
          <div className="flex flex-col items-center">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`l-${i}`}
                style={{
                  width: i % 2 === 0 ? "8px" : "6px",
                  height: "12px",
                  border: "2px solid #8B7355",
                  borderRadius: i % 2 === 0 ? "4px" : "2px",
                  marginTop: i === 0 ? 0 : "-2px",
                  background: "transparent",
                }}
              />
            ))}
          </div>
          {/* Right chain */}
          <div className="flex flex-col items-center">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={`r-${i}`}
                style={{
                  width: i % 2 === 0 ? "8px" : "6px",
                  height: "12px",
                  border: "2px solid #8B7355",
                  borderRadius: i % 2 === 0 ? "4px" : "2px",
                  marginTop: i === 0 ? 0 : "-2px",
                  background: "transparent",
                }}
              />
            ))}
          </div>
        </div>

        {/* Wooden plank */}
        <motion.div
          className="relative flex flex-col items-center justify-center cursor-pointer"
          style={{
            width: "260px",
            minHeight: "160px",
            borderRadius: "12px",
            background: "linear-gradient(135deg, #A0522D 0%, #8B6914 30%, #C49A6C 50%, #8B6914 70%, #A0522D 100%)",
            border: "4px solid #5C3317",
            boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 2px 4px rgba(255,255,255,0.1)",
            padding: "24px 20px",
            pointerEvents: canTap ? "auto" : "none",
          }}
          whileTap={canTap ? { scale: 0.97 } : {}}
          onClick={handleTap}
        >
          {/* Wood grain lines */}
          {[20, 45, 70, 95, 120].map((y) => (
            <div
              key={y}
              style={{
                position: "absolute",
                top: `${y}px`,
                left: "8px",
                right: "8px",
                height: "1px",
                background: "rgba(92, 51, 23, 0.25)",
              }}
            />
          ))}

          {/* Quote text */}
          <p
            className="text-center font-bold leading-7"
            style={{
              color: "#FFF8E7",
              textShadow: "1px 1px 2px rgba(0,0,0,0.3)",
              fontSize: "18px",
              position: "relative",
              zIndex: 1,
            }}
          >
            {quote}
          </p>

          {/* Tap hint */}
          {canTap && (
            <p
              className="mt-4 text-center"
              style={{
                fontFamily: "'Press Start 2P', monospace",
                fontSize: "6px",
                color: "rgba(255,248,231,0.5)",
                position: "relative",
                zIndex: 1,
              }}
            >
              tap to enter
            </p>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}
