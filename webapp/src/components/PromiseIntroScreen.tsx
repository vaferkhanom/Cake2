/**
 * PromiseIntroScreen — Pixel-art wooden plank intro screen.
 *
 * Shows once per session before the Dashboard. A horizontal wooden beam
 * slides in from the left (~3.5s), then a wooden plank drops from it
 * via chains (~3.5s). Total: 7 seconds. Both are pixel-art styled.
 * After landing, the plank becomes tappable to enter the app.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

// Persian quotes about promises
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

const INTRO_SHOWN_KEY = "promise-intro-shown";

export function shouldShowIntro(): boolean {
  try { return !sessionStorage.getItem(INTRO_SHOWN_KEY); }
  catch { return true; }
}

export function markIntroShown(): void {
  try { sessionStorage.setItem(INTRO_SHOWN_KEY, "1"); }
  catch { /* ignore */ }
}

// Pixel-art wood color palette
const W = {
  D1: "#5C3317", // dark outline
  D2: "#7A4B2A", // dark grain
  M1: "#A0522D", // mid wood
  M2: "#B8733A", // lighter mid
  L1: "#C49A6C", // light highlight
  L2: "#D4AA7C", // lightest
};

// Pixel-art horizontal beam sprite (a simple wood beam, ~80x8 px scaled up)
const BEAM_SPRITE: string[][] = [
  [W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1],
  [W.D1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.M2,W.M1,W.L1,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.M1,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.M1,W.L1,W.M2,W.M1,W.L1,W.M2,W.L1,W.M2,W.M1,W.L1,W.M2,W.M1,W.L1,W.M2,W.L1,W.M2,W.M1,W.L1,W.M2,W.M1,W.L1,W.M2,W.L1,W.M2,W.M1,W.L1,W.M2,W.M1,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.D2,W.M1,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.M1,W.D1,W.D1],
  [W.D1,W.M1,W.L1,W.M1,W.M2,W.L1,W.M1,W.L1,W.M2,W.L1,W.M1,W.L1,W.M2,W.L1,W.M1,W.L1,W.M2,W.L1,W.M1,W.L1,W.M2,W.L1,W.M1,W.L1,W.M2,W.L1,W.M1,W.L1,W.M2,W.L1,W.M1,W.L1,W.M2,W.L1,W.M1,W.L1,W.M2,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.M1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.L1,W.M2,W.M1,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D1,W.D1],
  [W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1],
];

// Pixel-art plank sprite (smaller, ~40x12 px scaled up)
const PLANK_SPRITE: string[][] = [
  // top border
  [W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1],
  // wood rows
  [W.D1,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.D1,W.D1],
  [W.D1,W.M2,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.M1,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M1,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.D1,W.D1],
  [W.D1,W.M2,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.M1,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.M2,W.D1,W.D1],
  // bottom border
  [W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1],
];

function drawPixelGrid(
  ctx: CanvasRenderingContext2D,
  grid: string[][],
  x: number,
  y: number,
  pixelSize: number,
) {
  for (let row = 0; row < grid.length; row++) {
    for (let col = 0; col < grid[row].length; col++) {
      ctx.fillStyle = grid[row][col];
      ctx.fillRect(
        Math.floor(x + col * pixelSize),
        Math.floor(y + row * pixelSize),
        pixelSize,
        pixelSize,
      );
    }
  }
}

export default function PromiseIntroScreen({ onDone }: { onDone: () => void }) {
  const [phase, setPhase] = useState<"beam" | "plank" | "done">("beam");
  const [canTap, setCanTap] = useState(false);

  const quote = useMemo(() => QUOTES[Math.floor(Math.random() * QUOTES.length)], []);

  // Phase timing: beam slides in (3.5s) → plank drops (3.5s) → done
  useEffect(() => {
    const t1 = setTimeout(() => setPhase("plank"), 3500);
    const t2 = setTimeout(() => { setPhase("done"); setCanTap(true); }, 7000);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const handleTap = useCallback(() => {
    if (!canTap) return;
    markIntroShown();
    onDone();
  }, [canTap, onDone]);

  return (
    <div
      className="fixed inset-0 z-50"
      onClick={handleTap}
      style={{ pointerEvents: canTap ? "auto" : "none" }}
    >
      {/* Beam slides in from left — positioned in upper 30% */}
      <motion.div
        className="absolute"
        style={{ top: "25%", left: 0, pointerEvents: "none" }}
        initial={{ x: "-100vw" }}
        animate={{ x: "10vw" }}
        transition={{ duration: 3.5, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <canvas
          ref={(c) => {
            if (!c) return;
            const ctx = c.getContext("2d");
            if (!ctx) return;
            const ps = 4; // pixel size for beam
            c.width = BEAM_SPRITE[0].length * ps;
            c.height = BEAM_SPRITE.length * ps;
            c.style.width = (BEAM_SPRITE[0].length * ps) + "px";
            c.style.height = (BEAM_SPRITE.length * ps) + "px";
            drawPixelGrid(ctx, BEAM_SPRITE, 0, 0, ps);
          }}
          style={{ imageRendering: "pixelated" }}
        />
      </motion.div>

      {/* Plank drops from the beam — centered below the beam */}
      {phase !== "beam" && (
        <motion.div
          className="absolute flex flex-col items-center"
          style={{
            top: "calc(25% + 32px)", // just below the beam
            left: "50%",
            transform: "translateX(-50%)",
            pointerEvents: "none",
          }}
          initial={{ y: "-40vh", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 3.5, ease: [0.34, 1.56, 0.64, 1] }}
        >
          {/* Chains */}
          <div className="flex justify-between" style={{ width: "100px" }}>
            <div className="flex flex-col items-center">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={`l-${i}`}
                  style={{
                    width: i % 2 === 0 ? "6px" : "5px",
                    height: "8px",
                    border: "2px solid #7A4B2A",
                    borderRadius: i % 2 === 0 ? "3px" : "1px",
                    marginTop: i === 0 ? 0 : "-1px",
                    background: "transparent",
                  }}
                />
              ))}
            </div>
            <div className="flex flex-col items-center">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={`r-${i}`}
                  style={{
                    width: i % 2 === 0 ? "6px" : "5px",
                    height: "8px",
                    border: "2px solid #7A4B2A",
                    borderRadius: i % 2 === 0 ? "3px" : "1px",
                    marginTop: i === 0 ? 0 : "-1px",
                    background: "transparent",
                  }}
                />
              ))}
            </div>
          </div>

          {/* Pixel-art plank */}
          <div className="flex flex-col items-center justify-center" style={{ position: "relative" }}>
            <canvas
              ref={(c) => {
                if (!c) return;
                const ctx = c.getContext("2d");
                if (!ctx) return;
                const ps = 4;
                c.width = PLANK_SPRITE[0].length * ps;
                c.height = PLANK_SPRITE.length * ps;
                c.style.width = (PLANK_SPRITE[0].length * ps) + "px";
                c.style.height = (PLANK_SPRITE.length * ps) + "px";
                drawPixelGrid(ctx, PLANK_SPRITE, 0, 0, ps);
              }}
              style={{ imageRendering: "pixelated" }}
            />
            {/* Quote text overlaid on plank */}
            <p
              className="absolute text-center font-bold"
              style={{
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                color: "#FFF8E7",
                textShadow: "1px 1px 2px rgba(0,0,0,0.5)",
                fontSize: "13px",
                whiteSpace: "nowrap",
                pointerEvents: "none",
              }}
            >
              {quote}
            </p>
          </div>

          {/* Tap hint */}
          {canTap && (
            <p
              className="mt-6 text-center"
              style={{
                fontFamily: "'Press Start 2P', monospace",
                fontSize: "6px",
                color: "rgba(255,248,231,0.6)",
                pointerEvents: "none",
              }}
            >
              tap to enter
            </p>
          )}
        </motion.div>
      )}
    </div>
  );
}
