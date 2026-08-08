/**
 * PromiseIntroScreen — Pixel-art wooden plank intro screen.
 *
 * Shows once per session before the Dashboard. A horizontal wooden beam
 * slides in from the left with a plank hanging from it via chains.
 * Total: ~7 seconds. After landing, the plank becomes tappable.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

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
  D1: "#5C3317",
  D2: "#7A4B2A",
  M1: "#A0522D",
  M2: "#B8733A",
  L1: "#C49A6C",
  L2: "#D4AA7C",
};

// Beam sprite (~40x8 pixels)
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

// Plank sprite (~32x10 pixels)
const PLANK_SPRITE: string[][] = [
  [W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1],
  [W.D1,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M2,W.L1,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.L1,W.M2,W.L1,W.M1,W.L2,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.D1,W.D1],
  [W.D1,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.L2,W.M1,W.M2,W.L1,W.M1,W.D1,W.D1],
  [W.D1,W.M2,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M1,W.D2,W.M2,W.D1,W.D1],
  [W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1,W.D1],
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
  const [canTap, setCanTap] = useState(false);
  const quote = useMemo(() => QUOTES[Math.floor(Math.random() * QUOTES.length)], []);

  useEffect(() => {
    const t = setTimeout(() => setCanTap(true), 7000);
    return () => clearTimeout(t);
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
      {/* Beam + plank assembly — one connected unit sliding in from left */}
      <motion.div
        className="absolute"
        style={{
          top: "22%",
          left: 0,
          pointerEvents: "none",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
        initial={{ x: "-80vw" }}
        animate={{ x: "15vw" }}
        transition={{ duration: 7, ease: [0.25, 0.1, 0.25, 1] }}
      >
        {/* Horizontal beam — responsive width via canvas scaling */}
        <BeamCanvas />

        {/* Chains + plank — hangs directly below the beam, always attached */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          {/* Chains */}
          <div className="flex justify-between" style={{ width: "120px" }}>
            <ChainStrand />
            <ChainStrand />
          </div>

          {/* Plank */}
          <PlankWithQuote quote={quote} canTap={canTap} />
        </div>
      </motion.div>
    </div>
  );
}

// Responsive beam canvas — 65vw wide
function BeamCanvas() {
  return (
    <canvas
      ref={(c) => {
        if (!c) return;
        const ctx = c.getContext("2d");
        if (!ctx) return;
        const spriteW = BEAM_SPRITE[0].length;
        const spriteH = BEAM_SPRITE.length;
        // Scale to 65vw while keeping pixel-art look
        const targetW = Math.round(window.innerWidth * 0.65);
        const ps = targetW / spriteW;
        c.width = targetW;
        c.height = spriteH * ps;
        c.style.width = targetW + "px";
        c.style.height = Math.round(spriteH * ps) + "px";
        drawPixelGrid(ctx, BEAM_SPRITE, 0, 0, ps);
      }}
      style={{ imageRendering: "pixelated" as const }}
    />
  );
}

// Plank canvas + quote text — ~50vw wide
function PlankWithQuote({ quote, canTap }: { quote: string; canTap: boolean }) {
  return (
    <div style={{ position: "relative" }}>
      <canvas
        ref={(c) => {
          if (!c) return;
          const ctx = c.getContext("2d");
          if (!ctx) return;
          const spriteW = PLANK_SPRITE[0].length;
          const spriteH = PLANK_SPRITE.length;
          const targetW = Math.round(window.innerWidth * 0.50);
          const ps = targetW / spriteW;
          c.width = targetW;
          c.height = spriteH * ps;
          c.style.width = targetW + "px";
          c.style.height = Math.round(spriteH * ps) + "px";
          drawPixelGrid(ctx, PLANK_SPRITE, 0, 0, ps);
        }}
        style={{ imageRendering: "pixelated" as const }}
      />

      {/* Quote text constrained to plank width */}
      <div
        className="absolute flex items-center justify-center"
        style={{
          top: "10%",
          left: "10%",
          right: "10%",
          bottom: "10%",
        }}
      >
        <p
          className="text-center font-bold"
          style={{
            color: "#FFF8E7",
            textShadow: "2px 2px 4px rgba(0,0,0,0.8), 0 0 8px rgba(0,0,0,0.4)",
            fontSize: "15px",
            lineHeight: "1.3",
            pointerEvents: "none",
            width: "100%",
          }}
        >
          {quote}
        </p>
      </div>

      {/* Tap hint */}
      {canTap && (
        <p
          className="absolute text-center"
          style={{
            bottom: "-30px",
            left: "50%",
            transform: "translateX(-50%)",
            fontFamily: "'Press Start 2P', monospace",
            fontSize: "8px",
            color: "rgba(255,248,231,0.6)",
            whiteSpace: "nowrap",
            pointerEvents: "none",
          }}
        >
          tap to enter
        </p>
      )}
    </div>
  );
}

// Reusable chain strand
function ChainStrand() {
  return (
    <div className="flex flex-col items-center">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
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
  );
}
