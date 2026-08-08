/**
 * Caketich Easter Egg — pixel-art Stitch eating cake.
 *
 * Triggered by tapping the score 10 times on Profile.
 * After 20 seconds, "caketich" text drops. Then tap 5 times to "eat"
 * the text bite by bite, and exit on the 5th tap.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// Pixel art color palette
const C = {
  _: "transparent",
  B: "#3B6BAA",
  D: "#2A4F7A",
  L: "#6BA3D6",
  W: "#FFFFFF",
  K: "#1A1A2E",
  P: "#FFB6C1",
  N: "#8B6914",
  T: "#A0522D",
  CK: "#FFEFD5",
  CR: "#FF6B6B",
  CB: "#8B4513",
  CG: "#90EE90",
  H: "#5A3A1A",
  M: "#CC3333",
  S: "#E8D5B7",
};

const STITCH_BODY = [
  [C._, C._, C.D, C.B, C.B, C._, C._, C._, C._, C._, C._, C.D, C.B, C.B, C._, C._],
  [C._, C.D, C.B, C.P, C.B, C.B, C._, C._, C._, C._, C.D, C.B, C.P, C.B, C.B, C._],
  [C._, C.D, C.B, C.P, C.P, C.B, C.B, C._, C._, C.D, C.B, C.P, C.P, C.B, C.B, C._],
  [C._, C._, C.D, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C._, C._],
  [C._, C._, C.D, C.B, C.W, C.K, C.B, C.B, C.B, C.B, C.W, C.K, C.B, C.D, C._, C._],
  [C._, C._, C.D, C.B, C.B, C.B, C.B, C.D, C.D, C.B, C.B, C.B, C.B, C.D, C._, C._],
  [C._, C._, C._, C.D, C.B, C.B, C.M, C.M, C.M, C.B, C.B, C.B, C.D, C._, C._, C._],
  [C._, C._, C._, C._, C.D, C.M, C.W, C.W, C.M, C.B, C.B, C.D, C._, C._, C._, C._],
  [C._, C._, C._, C._, C.D, C.B, C.B, C.B, C.B, C.B, C.D, C._, C._, C._, C._, C._],
  [C._, C._, C._, C.D, C.B, C.L, C.L, C.L, C.L, C.B, C.B, C.D, C._, C._, C._, C._],
  [C._, C._, C._, C.D, C.B, C.L, C.L, C.L, C.L, C.B, C.B, C.D, C._, C._, C._, C._],
  [C._, C._, C._, C.D, C.B, C.B, C.B, C.B, C.B, C.B, C.H, C.H, C.D, C._, C._, C._],
  [C._, C._, C._, C._, C.D, C.B, C.B, C.B, C.B, C.D, C._, C.H, C.H, C.D, C._, C._],
  [C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N],
  [C._, C._, C._, C._, C._, C.CR, C.CR, C.CR, C.CR, C.CR, C._, C._, C._, C._, C._, C._],
  [C._, C._, C._, C._, C.CK, C.CK, C.CK, C.CK, C.CK, C.CK, C._, C._, C._, C._, C._, C._],
  [C._, C._, C._, C._, C.CK, C.CB, C.CK, C.CK, C.CB, C.CK, C._, C._, C._, C._, C._, C._],
  [C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N],
  [C.T, C._, C._, C._, C._, C._, C.T, C._, C._, C.T, C._, C._, C._, C._, C._, C.T],
  [C.T, C._, C._, C._, C._, C._, C.T, C._, C._, C.T, C._, C._, C._, C._, C._, C.T],
];

const PIXEL = 16;
const TOTAL_TAPS = 5;
const CAKETICH_TEXT = "caketich";
// Letters to remove per tap (progressive: 2, 2, 2, 1, 1 = 8 total)
const TAPS_LETTERS = [2, 2, 2, 1, 1];

export default function CaketichEasterEgg({ onClose }: { onClose: () => void }) {
  const [elapsed, setElapsed] = useState(0);
  const [dropped, setDropped] = useState(false);
  const [scatter, setScatter] = useState(false);
  const [tapsDone, setTapsDone] = useState(0);
  const startRef = useRef(Date.now());

  const scatterOffsets = useMemo(() => {
    return STITCH_BODY.map((row) =>
      row.map(() => ({
        tx: (Math.random() - 0.5) * 200,
        ty: (Math.random() - 0.5) * 200,
        rot: (Math.random() - 0.5) * 30,
        delay: Math.random() * 200,
      }))
    );
  }, []);

  // 20-second timer
  useEffect(() => {
    const iv = setInterval(() => {
      const sec = Math.floor((Date.now() - startRef.current) / 1000);
      setElapsed(sec);
      if (sec >= 20 && !dropped) {
        setDropped(true);
        setTimeout(() => setScatter(true), 600);
      }
    }, 500);
    return () => clearInterval(iv);
  }, [dropped]);

  // Calculate how much of the text is visible
  const lettersVisible = useMemo(() => {
    let removed = 0;
    for (let i = 0; i < tapsDone; i++) {
      removed += TAPS_LETTERS[i] || 0;
    }
    return Math.max(0, CAKETICH_TEXT.length - removed);
  }, [tapsDone]);

  const displayText = CAKETICH_TEXT.slice(0, lettersVisible);

  // Tap handler — only works after text has dropped
  const handleTap = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (!dropped) return;
    if (tapsDone >= TOTAL_TAPS) return;

    const newTaps = tapsDone + 1;
    setTapsDone(newTaps);

    if (newTaps >= TOTAL_TAPS) {
      // All text eaten — exit after a short delay
      setTimeout(() => onClose(), 300);
    }
  }, [dropped, tapsDone, onClose]);

  const canExit = dropped;
  const remainingTaps = TOTAL_TAPS - tapsDone;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center"
      style={{ background: "linear-gradient(180deg, #1a1040 0%, #2a1a50 50%, #3a2060 100%)" }}
      onClick={canExit ? handleTap : undefined}
    >
      {/* Caketich text drop — pixel font, eats away on tap */}
      {dropped && lettersVisible > 0 && (
        <div
          className="absolute top-0 left-0 right-0 text-center"
          style={{
            animation: "caketichDrop 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards",
            zIndex: 60,
          }}
        >
          <span
            className="text-4xl font-pixel"
            style={{
              color: "#FF6B6B",
              textShadow: "3px 3px 0 #CC3333, 6px 6px 0 rgba(0,0,0,0.3)",
              letterSpacing: "2px",
            }}
          >
            {displayText}
          </span>
        </div>
      )}

      {/* Exit hint — pixel font */}
      {dropped && tapsDone < TOTAL_TAPS && (
        <div
          className="absolute top-16 text-center"
          style={{
            fontFamily: "'Press Start 2P', monospace",
            fontSize: "7px",
            color: "#C4B8D9",
            zIndex: 61,
            animation: "pulse 2s ease-in-out infinite",
          }}
        >
          {remainingTaps} bar bezan!
        </div>
      )}

      {/* Pixel art scene — per-pixel scatter */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        {STITCH_BODY.map((row, y) => (
          <div key={y} style={{ display: "flex" }}>
            {row.map((color, x) => {
              const offset = scatterOffsets[y][x];
              const isTransparent = color === C._;
              let transform = "none";
              let transition = "none";
              if (scatter && !isTransparent) {
                transform = `translate(${offset.tx}px, ${offset.ty}px) rotate(${offset.rot}deg)`;
                transition = `transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${offset.delay}ms`;
              }
              return (
                <div
                  key={x}
                  style={{
                    width: PIXEL,
                    height: PIXEL,
                    backgroundColor: color,
                    transform,
                    transition,
                    opacity: scatter && isTransparent ? 0 : 1,
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* Eating indicator */}
      <div
        className="mt-6 text-center"
        style={{
          fontFamily: "'Press Start 2P', monospace",
          fontSize: "10px",
          color: "#C4B8D9",
          animation: "pulse 2s ease-in-out infinite",
        }}
      >
        nom nom nom...
      </div>

      {/* Timer */}
      <div
        className="absolute bottom-8"
        style={{
          fontFamily: "'Press Start 2P', monospace",
          fontSize: "8px",
          color: "#6E6878",
        }}
      >
        {Math.min(elapsed, 20)}s / 20s
      </div>

      {/* Wait hint before drop */}
      {!dropped && (
        <div
          className="absolute top-8"
          style={{
            fontFamily: "'Press Start 2P', monospace",
            fontSize: "7px",
            color: "#6E6878",
          }}
        >
          wait...
        </div>
      )}

      <style>{`
        @keyframes caketichDrop {
          0% { transform: translateY(-200px); opacity: 0; }
          60% { transform: translateY(10px); opacity: 1; }
          80% { transform: translateY(-5px); }
          100% { transform: translateY(0); opacity: 1; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
