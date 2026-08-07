/**
 * Caketich Easter Egg — pixel-art Stitch eating cake.
 *
 * Triggered by tapping the score 10 times on Profile.
 * After 60 seconds, "caketich" text drops and scatters the scene.
 * 
 * PIXEL-ART: uses Press Start 2P font, large pixel sprites,
 * and real per-pixel scatter effect.
 */

import { useEffect, useMemo, useRef, useState } from "react";

// Pixel art color palette
const C = {
  _: "transparent",
  B: "#3B6BAA", // blue fur (body)
  D: "#2A4F7A", // dark blue (outline/shadow)
  L: "#6BA3D6", // light blue (belly)
  W: "#FFFFFF", // white (eyes, teeth)
  K: "#1A1A2E", // black (pupils, nose)
  P: "#FFB6C1", // pink (inner ear)
  N: "#8B6914", // brown (table)
  T: "#A0522D", // dark brown (table leg)
  CK: "#FFEFD5", // cake cream
  CR: "#FF6B6B", // cake red (strawberry)
  CB: "#8B4513", // cake brown (chocolate)
  CG: "#90EE90", // cake green (mint)
  H: "#5A3A1A", // hand color
  M: "#CC3333", // mouth messy (red/cake)
  S: "#E8D5B7", // skin tone (face area)
};

// Stitch pixel art — 16x20 grid
const STITCH_BODY = [
  // Row 0-2: ears
  [C._, C._, C.D, C.B, C.B, C._, C._, C._, C._, C._, C._, C.D, C.B, C.B, C._, C._],
  [C._, C.D, C.B, C.P, C.B, C.B, C._, C._, C._, C._, C.D, C.B, C.P, C.B, C.B, C._],
  [C._, C.D, C.B, C.P, C.P, C.B, C.B, C._, C._, C.D, C.B, C.P, C.P, C.B, C.B, C._],
  // Row 3-5: head
  [C._, C._, C.D, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C.B, C._, C._],
  [C._, C._, C.D, C.B, C.W, C.K, C.B, C.B, C.B, C.B, C.W, C.K, C.B, C.D, C._, C._],
  [C._, C._, C.D, C.B, C.B, C.B, C.B, C.D, C.D, C.B, C.B, C.B, C.B, C.D, C._, C._],
  // Row 6-7: mouth area (messy!)
  [C._, C._, C._, C.D, C.B, C.B, C.M, C.M, C.M, C.B, C.B, C.B, C.D, C._, C._, C._],
  [C._, C._, C._, C._, C.D, C.M, C.W, C.W, C.M, C.B, C.B, C.D, C._, C._, C._, C._],
  // Row 8-10: body
  [C._, C._, C._, C._, C.D, C.B, C.B, C.B, C.B, C.B, C.D, C._, C._, C._, C._, C._],
  [C._, C._, C._, C.D, C.B, C.L, C.L, C.L, C.L, C.B, C.B, C.D, C._, C._, C._, C._],
  [C._, C._, C._, C.D, C.B, C.L, C.L, C.L, C.L, C.B, C.B, C.D, C._, C._, C._, C._],
  // Row 11-12: arm reaching for cake
  [C._, C._, C._, C.D, C.B, C.B, C.B, C.B, C.B, C.B, C.H, C.H, C.D, C._, C._, C._],
  [C._, C._, C._, C._, C.D, C.B, C.B, C.B, C.B, C.D, C._, C.H, C.H, C.D, C._, C._],
  // Row 13: table
  [C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N],
  // Row 14-16: cake on table
  [C._, C._, C._, C._, C._, C.CR, C.CR, C.CR, C.CR, C.CR, C._, C._, C._, C._, C._, C._],
  [C._, C._, C._, C._, C.CK, C.CK, C.CK, C.CK, C.CK, C.CK, C._, C._, C._, C._, C._, C._],
  [C._, C._, C._, C._, C.CK, C.CB, C.CK, C.CK, C.CB, C.CK, C._, C._, C._, C._, C._, C._],
  // Row 17-19: table bottom + legs
  [C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N, C.N],
  [C.T, C._, C._, C._, C._, C._, C.T, C._, C._, C.T, C._, C._, C._, C._, C._, C.T],
  [C.T, C._, C._, C._, C._, C._, C.T, C._, C._, C.T, C._, C._, C._, C._, C._, C.T],
];

const PIXEL = 16; // px per pixel (increased from 6)

export default function CaketichEasterEgg({ onClose }: { onClose: () => void }) {
  const [elapsed, setElapsed] = useState(0);
  const [dropped, setDropped] = useState(false);
  const [scatter, setScatter] = useState(false);
  const startRef = useRef(Date.now());

  // Generate stable random offsets for each pixel (for scatter effect)
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

  // 60-second timer
  useEffect(() => {
    const iv = setInterval(() => {
      const sec = Math.floor((Date.now() - startRef.current) / 1000);
      setElapsed(sec);
      if (sec >= 60 && !dropped) {
        setDropped(true);
        setTimeout(() => setScatter(true), 600);
      }
    }, 500);
    return () => clearInterval(iv);
  }, [dropped]);

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center"
      style={{ background: "linear-gradient(180deg, #1a1040 0%, #2a1a50 50%, #3a2060 100%)" }}
      onClick={onClose}
    >
      {/* Caketich text drop — pixel-art font */}
      {dropped && (
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
            caketich
          </span>
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

      {/* Eating animation indicator — pixel font */}
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

      {/* Timer — pixel font */}
      <div
        className="absolute bottom-8"
        style={{
          fontFamily: "'Press Start 2P', monospace",
          fontSize: "8px",
          color: "#6E6878",
        }}
      >
        {elapsed}s / 60s
      </div>

      {/* Tap to exit hint — pixel font */}
      <div
        className="absolute top-8"
        style={{
          fontFamily: "'Press Start 2P', monospace",
          fontSize: "7px",
          color: "#6E6878",
        }}
      >
        tap to exit
      </div>

      {/* CSS animations */}
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
