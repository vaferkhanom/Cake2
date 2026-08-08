/**
 * Live Tehran Sky Background — Pixel-Art Canvas Renderer
 *
 * Pixel-art sky + sea with: sun/moon sprites, twinkling stars,
 * shooting stars, water with seaweed, 4 fish shape variants,
 * Bikini Bottom island with SpongeBob/Patrick/Squidward,
 * and Tyrion's boat with rare sea creature surfacing.
 */

import { useEffect, useRef, useState } from "react";
import SunCalc from "suncalc3";

// ── Tehran coordinates ──────────────────────────────────────────────────────
const TEHRAN_LAT = 35.6892;
const TEHRAN_LON = 51.3890;
const WATER_HEIGHT_FRACTION = 0.40;

// ── Color helpers ───────────────────────────────────────────────────────────
function lerpColor(a: number[], b: number[], t: number): number[] {
  return a.map((v, i) => Math.round(v + (b[i] - v) * t));
}
function rgb(c: number[]): string { return `rgb(${c[0]},${c[1]},${c[2]})`; }
function rgba(c: number[], a: number): string { return `rgba(${c[0]},${c[1]},${c[2]},${a})`; }

// ── Sky palettes ────────────────────────────────────────────────────────────
const SKY_PALETTES = {
  nightDeep: [[8,10,26],[12,16,35],[16,18,42],[18,14,50],[20,12,45],[14,10,30]],
  nightLight: [[14,18,38],[20,24,52],[28,22,58],[35,22,55],[40,20,50],[28,18,40]],
  dusk: [[35,28,65],[65,35,70],[110,50,65],[180,80,60],[200,110,60],[150,80,50]],
  golden: [[70,110,170],[120,160,210],[190,190,180],[240,180,100],[255,200,120],[240,170,90]],
  day: [[60,120,200],[100,160,220],[140,190,235],[180,215,245],[210,230,250],[190,215,235]],
  dayBright: [[40,100,190],[70,140,220],[110,180,240],[150,205,245],[185,225,250],[170,215,245]],
};

function getSkyColors(sunAlt: number): number[][] {
  let from: number[][], to: number[][], t: number;
  if (sunAlt < -18) return SKY_PALETTES.nightDeep;
  if (sunAlt < -12) { from = SKY_PALETTES.nightDeep; to = SKY_PALETTES.nightLight; t = (sunAlt + 18) / 6; }
  else if (sunAlt < -6) { from = SKY_PALETTES.nightLight; to = SKY_PALETTES.dusk; t = (sunAlt + 12) / 6; }
  else if (sunAlt < 0) { from = SKY_PALETTES.dusk; to = SKY_PALETTES.golden; t = (sunAlt + 6) / 6; }
  else if (sunAlt < 45) { from = SKY_PALETTES.golden; to = SKY_PALETTES.day; t = sunAlt / 45; }
  else { from = SKY_PALETTES.day; to = SKY_PALETTES.dayBright; t = (sunAlt - 45) / 45; }
  t = Math.max(0, Math.min(1, t));
  return from.map((c, i) => lerpColor(c, to[i], t));
}

// ── Sun sprites (8x8) ──────────────────────────────────────────────────────
const SUN_SPRITES = {
  high: [[0,0,2,2,2,2,0,0],[0,2,1,1,1,1,2,0],[2,1,1,2,2,1,1,2],[2,1,2,1,1,2,1,2],[2,1,2,1,1,2,1,2],[2,1,1,2,2,1,1,2],[0,2,1,1,1,1,2,0],[0,0,2,2,2,2,0,0]],
  low: [[0,0,3,3,3,3,0,0],[0,3,4,3,3,4,3,0],[3,4,3,3,3,3,4,3],[3,3,3,4,4,3,3,3],[3,3,3,4,4,3,3,3],[3,4,3,3,3,3,4,3],[0,3,4,3,3,4,3,0],[0,0,3,3,3,3,0,0]],
};
const SUN_COLORS = { high: ["","#FFF8E1","#FFD54F","#FFB300",""], low: ["","#FF6644","#FF8C42","#CC4422","#993311"] };

// ── Moon sprites (10x10, 8 phases) ─────────────────────────────────────────
const MOON_SPRITES: number[][][] = [
  Array.from({length:10},()=>[0,0,0,0,0,0,0,0,0,0]),
  [[0,0,0,0,0,0,0,1,1,0],[0,0,0,0,0,0,1,1,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,1,0,0],[0,0,0,0,0,0,0,1,1,0]],
  [[0,0,0,0,0,1,1,1,1,0],[0,0,0,0,0,1,1,1,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,1,0,0],[0,0,0,0,0,1,1,1,1,0]],
  [[0,0,0,1,1,1,1,1,1,0],[0,0,1,1,1,1,1,1,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,0,1,1,1,1,1,1,0,0],[0,0,0,1,1,1,1,1,1,0]],
  [[0,0,1,1,1,1,1,1,0,0],[0,1,1,1,1,1,1,1,1,0],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,1,0],[0,0,1,1,1,1,1,1,0,0]],
  [[0,0,1,1,1,1,1,0,0,0],[0,0,1,1,1,1,1,1,0,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,1,1,1,1,1,1,0,0],[0,0,1,1,1,1,1,0,0,0]],
  [[0,1,1,1,1,0,0,0,0,0],[0,0,1,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,1,1,1,0,0,0,0,0],[0,1,1,1,1,0,0,0,0,0]],
  [[0,1,1,0,0,0,0,0,0,0],[0,0,1,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,1,1,0,0,0,0,0,0],[0,1,1,0,0,0,0,0,0,0]],
];
function getMoonPhaseIndex(pv: number): number { return Math.round(pv * 8) % 8; }

// ── Stars ───────────────────────────────────────────────────────────────────
interface Star { x: number; y: number; size: number; twinklePhase: number; twinkleSpeed: number; }
function generateStars(n: number): Star[] {
  return Array.from({ length: n }, () => ({
    x: Math.random(), y: Math.random() * 0.65,
    size: Math.random() > 0.7 ? 2 : 1,
    twinklePhase: Math.random() * Math.PI * 2,
    twinkleSpeed: 1.5 + Math.random() * 3,
  }));
}

// ── Shooting star ───────────────────────────────────────────────────────────
interface ShootingStar { x: number; y: number; angle: number; progress: number; active: boolean; }

// ── Seaweed ─────────────────────────────────────────────────────────────────
interface Seaweed { x: number; height: number; swaySpeed: number; swayPhase: number; color: string; }
function generateSeaweed(n: number): Seaweed[] {
  const greens = ["#2D5A27","#3A7A33","#1E4D1A","#4A8A40","#256B1F"];
  return Array.from({ length: n }, () => ({
    x: Math.random(), height: 30 + Math.random() * 50,
    swaySpeed: 0.8 + Math.random() * 1.5,
    swayPhase: Math.random() * Math.PI * 2,
    color: greens[Math.floor(Math.random() * greens.length)],
  }));
}

// ── Fish with shape variants ────────────────────────────────────────────────
interface Fish { x: number; y: number; speed: number; size: number; color: string; bobPhase: number; shape: number; }
function generateFish(n: number): Fish[] {
  const colors = ["#FF6B6B","#FFD93D","#6BCB77","#4D96FF","#FF8FB1","#FFA07A","#98D8C8","#DDA0DD"];
  return Array.from({ length: n }, () => ({
    x: Math.random(), y: Math.random(),
    speed: 0.0002 + Math.random() * 0.0006,
    size: 2 + Math.floor(Math.random() * 3),
    color: colors[Math.floor(Math.random() * colors.length)],
    bobPhase: Math.random() * Math.PI * 2,
    shape: Math.floor(Math.random() * 4), // 0-3 = 4 shape variants
  }));
}

// ── Fish shape drawing functions ────────────────────────────────────────────
function drawFishA(ctx: CanvasRenderingContext2D, x: number, y: number, s: number, color: string) {
  // Classic oval fish
  ctx.fillStyle = color;
  ctx.fillRect(x + s, y, s * 3, s);
  ctx.fillRect(x, y + s, s * 5, s);
  ctx.fillRect(x + s, y + s * 2, s * 3, s);
  // Tail
  ctx.fillRect(x + s * 4, y - s, s, s);
  ctx.fillRect(x + s * 4, y + s * 2, s, s);
  // Eye
  ctx.fillStyle = "#FFF";
  ctx.fillRect(x + s * 3, y + s * 0.3, s, s);
  ctx.fillStyle = "#111";
  ctx.fillRect(x + s * 3.3, y + s * 0.5, s * 0.5, s * 0.5);
}

function drawFishB(ctx: CanvasRenderingContext2D, x: number, y: number, s: number, color: string) {
  // Round/chubby fish
  ctx.fillStyle = color;
  ctx.fillRect(x + s, y, s * 2, s);
  ctx.fillRect(x, y + s, s * 4, s);
  ctx.fillRect(x, y + s * 2, s * 4, s);
  ctx.fillRect(x + s, y + s * 3, s * 2, s);
  // Round tail
  ctx.fillRect(x + s * 3, y - s * 0.5, s, s * 4);
  ctx.fillRect(x + s * 4, y, s, s * 3);
  // Eye
  ctx.fillStyle = "#FFF";
  ctx.fillRect(x + s * 0.5, y + s * 0.5, s, s);
  ctx.fillStyle = "#111";
  ctx.fillRect(x + s * 0.7, y + s * 0.7, s * 0.5, s * 0.5);
  // Stripe
  ctx.fillStyle = "rgba(255,255,255,0.3)";
  ctx.fillRect(x + s * 1.5, y + s, s * 0.5, s * 2);
}

function drawFishC(ctx: CanvasRenderingContext2D, x: number, y: number, s: number, color: string) {
  // Long slender fish (like an eel/angelfish)
  ctx.fillStyle = color;
  ctx.fillRect(x, y + s, s * 6, s);
  ctx.fillRect(x + s, y, s * 4, s * 3);
  // Pointed tail
  ctx.fillRect(x + s * 5, y - s, s, s * 4);
  ctx.fillRect(x + s * 6, y, s, s * 2);
  // Dorsal fin
  ctx.fillStyle = "rgba(255,255,255,0.25)";
  ctx.fillRect(x + s * 2, y - s, s * 2, s);
  // Eye
  ctx.fillStyle = "#FFF";
  ctx.fillRect(x + s * 0.3, y + s * 0.5, s * 0.8, s * 0.8);
  ctx.fillStyle = "#111";
  ctx.fillRect(x + s * 0.5, y + s * 0.7, s * 0.4, s * 0.4);
}

function drawFishD(ctx: CanvasRenderingContext2D, x: number, y: number, s: number, color: string) {
  // Small school fish (tiny, simple)
  ctx.fillStyle = color;
  ctx.fillRect(x + s, y, s, s);
  ctx.fillRect(x, y + s, s * 3, s);
  ctx.fillRect(x + s, y + s * 2, s, s);
  // Tail
  ctx.fillRect(x + s * 2.5, y - s * 0.5, s * 0.5, s * 3);
  // Eye
  ctx.fillStyle = "#FFF";
  ctx.fillRect(x + s * 0.3, y + s * 0.3, s * 0.5, s * 0.5);
}

const FISH_DRAWERS = [drawFishA, drawFishB, drawFishC, drawFishD];

// ── Water pixels ────────────────────────────────────────────────────────────
interface WaterPixel { x: number; y: number; baseBrightness: number; phase: number; speed: number; }
function generateWaterPixels(cols: number, rows: number): WaterPixel[] {
  return Array.from({ length: rows * cols }, (_, i) => ({
    x: i % cols, y: Math.floor(i / cols),
    baseBrightness: 0.3 + Math.random() * 0.4,
    phase: Math.random() * Math.PI * 2,
    speed: 1 + Math.random() * 2,
  }));
}

// ── Tyrion's boat state ─────────────────────────────────────────────────────
interface BoatState {
  x: number; bobPhase: number; nextSurfacing: number; surfacing: boolean;
  surfacingProgress: number; surfacingX: number;
}

// ── Component ───────────────────────────────────────────────────────────────
export default function LiveSkyBackground({ reducedActivity = false }: { reducedActivity?: boolean } = {}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [now, setNow] = useState(() => new Date());
  const starsRef = useRef<Star[]>(generateStars(100));
  const seaweedRef = useRef<Seaweed[]>(generateSeaweed(12));
  const fishRef = useRef<Fish[]>(generateFish(8));
  const shootingRef = useRef<ShootingStar>({ x: 0, y: 0, angle: 0, progress: 0, active: false });
  const nextShootRef = useRef(Date.now() + 60000 + Math.random() * 180000);
  const boatRef = useRef<BoatState>({
    x: 0.12, bobPhase: Math.random() * Math.PI * 2,
    nextSurfacing: Date.now() + 30000 + Math.random() * 120000,
    surfacing: false, surfacingProgress: 0, surfacingX: 0,
  });
  const animFrameRef = useRef<number>(0);
  const waterPixelsRef = useRef<WaterPixel[]>([]);
  const lastAstronomyRef = useRef(0);
  const reducedActivityRef = useRef(reducedActivity);

  useEffect(() => { reducedActivityRef.current = reducedActivity; }, [reducedActivity]);

  useEffect(() => {
    const iv = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let currentSunAlt = 0, currentSunAz = 0, currentMoonAlt = 0, currentMoonAz = 0;
    let currentMoonIllum = { fraction: 0, phaseValue: 0, angle: 0 };
    let currentIsNight = false, currentIsDusk = false, currentStarOpacity = 0;
    let currentSkyColors = SKY_PALETTES.nightDeep;

    function recomputeAstronomy(d: Date) {
      const sp = SunCalc.getPosition(d, TEHRAN_LAT, TEHRAN_LON);
      currentSunAlt = (sp.altitude * 180) / Math.PI;
      currentSunAz = sp.azimuth + Math.PI;
      const mp = SunCalc.getMoonPosition(d, TEHRAN_LAT, TEHRAN_LON);
      currentMoonIllum = SunCalc.getMoonIllumination(d) as any;
      currentMoonAlt = (mp.altitude * 180) / Math.PI;
      currentMoonAz = mp.azimuth + Math.PI;
      currentIsNight = currentSunAlt < -6;
      currentIsDusk = currentSunAlt >= -6 && currentSunAlt < 0;
      currentStarOpacity = currentIsNight ? 1 : currentIsDusk ? Math.min(1, (-currentSunAlt) / 6) : 0;
      currentSkyColors = getSkyColors(currentSunAlt);
    }
    recomputeAstronomy(new Date());

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
      waterPixelsRef.current = generateWaterPixels(
        Math.ceil(window.innerWidth / 4),
        Math.ceil((window.innerHeight * WATER_HEIGHT_FRACTION) / 4),
      );
    };
    resize();
    window.addEventListener("resize", resize);

    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    function isMoonFullyVisible(mx: number, my: number, sz: number): boolean {
      const m = sz * 0.5;
      return mx > m && mx < W() - m && my > m && my < H() - m;
    }

    // ── Draw Bikini Bottom island + characters ────────────────────────────
    function drawIsland(w: number, waterY: number, waterH: number, nightFactor: number) {
      const ix = w * 0.78; // right side
      const iy = waterY + waterH * 0.12;
      const ps = 3; // pixel size for island characters

      // Night glow: warm ambient light around island
      if (nightFactor > 0.1) {
        ctx!.save();
        ctx!.globalAlpha = nightFactor * 0.35;
        ctx!.fillStyle = `rgba(255, 200, 100, 0.5)`;
        ctx!.fillRect(ix - ps * 18, iy - ps * 18, ps * 36, ps * 24);
        ctx!.restore();
      }

      // Sandy island base (organic shape, sits in water)
      const islandPixels: [number, number, string][] = [];
      // Sand mound
      for (let dx = -14; dx <= 14; dx++) {
        const h = Math.max(0, 6 - Math.abs(dx) * 0.4);
        for (let dy = 0; dy < h; dy++) {
          islandPixels.push([dx, -dy, dy < 2 ? "#C49A6C" : "#B8860B"]);
        }
      }
      // Underwater part
      for (let dx = -12; dx <= 12; dx++) {
        for (let dy = 1; dy <= 3; dy++) {
          islandPixels.push([dx, dy, `rgba(139,119,42,${0.5 - dy * 0.12})`]);
        }
      }
      // Palm tree trunk
      for (let dy = -6; dy >= -14; dy--) {
        islandPixels.push([2, dy, "#8B6914"]);
        if (dy % 2 === 0) islandPixels.push([3, dy, "#A0522D"]);
      }
      // Palm leaves
      const leaves: [number, number][] = [[-2,-14],[-1,-15],[0,-15],[1,-14],[3,-15],[4,-14],[2,-16]];
      for (const [dx, dy] of leaves) {
        islandPixels.push([dx, dy, "#2D5A27"]);
      }

      // Draw island
      for (const [dx, dy, color] of islandPixels) {
        ctx!.fillStyle = color;
        ctx!.fillRect(Math.floor(ix + dx * ps), Math.floor(iy + dy * ps), ps, ps);
      }

      // ── SpongeBob (square yellow, tiny) ──
      const sbx = ix - 6 * ps;
      const sby = iy - 8 * ps;
      // Body (yellow square)
      ctx!.fillStyle = "#FFD700";
      ctx!.fillRect(sbx, sby, ps * 4, ps * 4);
      // Pants (brown)
      ctx!.fillStyle = "#8B4513";
      ctx!.fillRect(sbx, sby + ps * 3, ps * 4, ps);
      // Eyes (white circles approximated)
      ctx!.fillStyle = "#FFF";
      ctx!.fillRect(sbx + ps * 0.5, sby + ps * 0.5, ps * 1.2, ps * 1.2);
      ctx!.fillRect(sbx + ps * 2.3, sby + ps * 0.5, ps * 1.2, ps * 1.2);
      ctx!.fillStyle = "#000";
      ctx!.fillRect(sbx + ps * 0.9, sby + ps * 0.8, ps * 0.5, ps * 0.5);
      ctx!.fillRect(sbx + ps * 2.7, sby + ps * 0.8, ps * 0.5, ps * 0.5);
      // Smile
      ctx!.fillStyle = "#000";
      ctx!.fillRect(sbx + ps * 1.2, sby + ps * 2.2, ps * 1.8, ps * 0.4);
      // Tie (red)
      ctx!.fillStyle = "#FF0000";
      ctx!.fillRect(sbx + ps * 1.5, sby + ps * 2.8, ps * 1, ps * 0.8);

      // ── Patrick (pink star) ──
      const px = ix + 5 * ps;
      const py = iy - 7 * ps;
      ctx!.fillStyle = "#FF69B4";
      // Star body
      ctx!.fillRect(px + ps, py, ps * 2, ps);
      ctx!.fillRect(px, py + ps, ps * 4, ps * 2);
      ctx!.fillRect(px + ps, py + ps * 3, ps * 2, ps);
      // Star points
      ctx!.fillRect(px, py - ps, ps, ps);
      ctx!.fillRect(px + ps * 3, py - ps, ps, ps);
      ctx!.fillRect(px - ps, py + ps, ps, ps);
      ctx!.fillRect(px + ps * 4, py + ps, ps, ps);
      // Eyes
      ctx!.fillStyle = "#000";
      ctx!.fillRect(px + ps * 0.8, py + ps * 0.8, ps * 0.5, ps * 0.5);
      ctx!.fillRect(px + ps * 2.5, py + ps * 0.8, ps * 0.5, ps * 0.5);
      // Shorts (green)
      ctx!.fillStyle = "#228B22";
      ctx!.fillRect(px, py + ps * 2.5, ps * 4, ps * 0.8);

      // ── Squidward (teal/turquoise, taller) ──
      const sqx = ix - 1 * ps;
      const sqy = iy - 10 * ps;
      // Head (teal, tall oval)
      ctx!.fillStyle = "#5F9EA0";
      ctx!.fillRect(sqx, sqy, ps * 3, ps * 3);
      ctx!.fillRect(sqx + ps * 0.5, sqy - ps, ps * 2, ps);
      // Nose (long)
      ctx!.fillStyle = "#4A8B8C";
      ctx!.fillRect(sqx + ps, sqy + ps * 1.5, ps, ps * 2);
      // Eyes (half-closed/bored)
      ctx!.fillStyle = "#FFF";
      ctx!.fillRect(sqx + ps * 0.3, sqy + ps * 0.3, ps * 1, ps * 0.6);
      ctx!.fillRect(sqx + ps * 1.7, sqy + ps * 0.3, ps * 1, ps * 0.6);
      ctx!.fillStyle = "#000";
      ctx!.fillRect(sqx + ps * 0.5, sqy + ps * 0.5, ps * 0.6, ps * 0.3);
      ctx!.fillRect(sqx + ps * 1.9, sqy + ps * 0.5, ps * 0.6, ps * 0.3);
      // Body (brown shirt)
      ctx!.fillStyle = "#8B7355";
      ctx!.fillRect(sqx, sqy + ps * 3, ps * 3, ps * 2);
      // Tentacles
      ctx!.fillStyle = "#5F9EA0";
      ctx!.fillRect(sqx, sqy + ps * 5, ps, ps * 2);
      ctx!.fillRect(sqx + ps * 2, sqy + ps * 5, ps, ps * 2);
    }

    // ── Draw Tyrion's boat + rare event ───────────────────────────────────
    function drawBoat(w: number, waterY: number, waterH: number, time: number, nightFactor: number, reduced: boolean) {
      const boat = boatRef.current;
      const bx = boat.x * w;
      const bob = Math.sin(time / 1200 + boat.bobPhase) * 3;
      const by = waterY + waterH * 0.2 + bob;
      const ps = 3;

      // Night lantern glow on boat
      if (nightFactor > 0.1) {
        ctx!.save();
        ctx!.globalAlpha = nightFactor * 0.4;
        ctx!.fillStyle = `rgba(255, 180, 60, 0.6)`;
        ctx!.fillRect(bx + ps * 1, by - ps * 3, ps * 3, ps * 2);
        // Wider glow radius
        ctx!.globalAlpha = nightFactor * 0.15;
        ctx!.fillRect(bx - ps * 4, by - ps * 8, ps * 18, ps * 14);
        ctx!.restore();
      }

      // Boat hull (wooden rowboat)
      ctx!.fillStyle = "#8B6914";
      // Hull bottom
      ctx!.fillRect(bx, by + ps * 3, ps * 10, ps);
      ctx!.fillRect(bx + ps, by + ps * 4, ps * 8, ps);
      ctx!.fillRect(bx + ps * 2, by + ps * 5, ps * 6, ps);
      // Hull sides
      ctx!.fillStyle = "#A0522D";
      ctx!.fillRect(bx, by + ps, ps * 10, ps * 2);
      // Rim
      ctx!.fillStyle = "#C49A6C";
      ctx!.fillRect(bx - ps, by, ps * 12, ps);
      // Mast
      ctx!.fillStyle = "#5C3317";
      ctx!.fillRect(bx + ps * 5, by - ps * 8, ps, ps * 9);
      // Sail (simple triangle approximated)
      ctx!.fillStyle = "rgba(240,230,210,0.8)";
      ctx!.fillRect(bx + ps * 6, by - ps * 7, ps * 3, ps);
      ctx!.fillRect(bx + ps * 6, by - ps * 6, ps * 4, ps);
      ctx!.fillRect(bx + ps * 6, by - ps * 5, ps * 5, ps);
      ctx!.fillRect(bx + ps * 6, by - ps * 4, ps * 5, ps);
      ctx!.fillRect(bx + ps * 6, by - ps * 3, ps * 4, ps);
      ctx!.fillRect(bx + ps * 6, by - ps * 2, ps * 3, ps);

      // Tyrion figure (tiny, seated)
      const tx = bx + ps * 2;
      const ty = by - ps * 2;
      // Head
      ctx!.fillStyle = "#DEB887";
      ctx!.fillRect(tx, ty, ps * 3, ps * 2);
      // Hair (dark brown)
      ctx!.fillStyle = "#3B2507";
      ctx!.fillRect(tx, ty - ps, ps * 3, ps);
      // Eyes
      ctx!.fillStyle = "#000";
      ctx!.fillRect(tx + ps * 0.5, ty + ps * 0.3, ps * 0.5, ps * 0.4);
      ctx!.fillRect(tx + ps * 2, ty + ps * 0.3, ps * 0.5, ps * 0.4);
      // Beard
      ctx!.fillStyle = "#5C3317";
      ctx!.fillRect(tx + ps * 0.5, ty + ps * 1.3, ps * 2, ps * 0.5);
      // Body (dark clothes)
      ctx!.fillStyle = "#1A1A2E";
      ctx!.fillRect(tx, ty + ps * 2, ps * 3, ps * 2);
      // Wine goblet (red)
      ctx!.fillStyle = "#8B0000";
      ctx!.fillRect(tx + ps * 3.5, ty + ps * 1.5, ps * 0.8, ps * 1.2);
      ctx!.fillStyle = "#CC0000";
      ctx!.fillRect(tx + ps * 3.3, ty + ps * 1, ps * 1.2, ps * 0.8);

      // Slow drift (frozen during reduced activity)
      if (!reduced) {
        boat.x += 0.00008;
        if (boat.x > 0.25) boat.x = 0.05;
      }

      // ── Rare surfacing event ─────────────────────────────────────────
      if (!reduced) {
        const t = Date.now();
        if (!boat.surfacing && t > boat.nextSurfacing) {
          boat.surfacing = true;
          boat.surfacingProgress = 0;
          boat.surfacingX = boat.x + (Math.random() - 0.5) * 0.08;
          boat.nextSurfacing = t + 45000 + Math.random() * 120000;
        }
      }
      if (boat.surfacing && !reduced) {
        boat.surfacingProgress += 0.008;
        if (boat.surfacingProgress >= 1) {
          boat.surfacing = false;
        } else {
          const sx = boat.surfacingX * w;
          const surfBob = Math.sin(boat.surfacingProgress * Math.PI) * 12;
          const sy = waterY + waterH * 0.25 - surfBob;
          // Tentacle silhouette emerging from water
          ctx!.fillStyle = `rgba(30, 60, 30, ${Math.sin(boat.surfacingProgress * Math.PI) * 0.7})`;
          // Tentacle
          ctx!.fillRect(sx, sy, ps * 2, ps * 4);
          ctx!.fillRect(sx - ps, sy - ps, ps, ps * 2);
          ctx!.fillRect(sx + ps * 2, sy - ps, ps, ps * 2);
          // Suction cups
          ctx!.fillStyle = `rgba(50, 100, 50, ${Math.sin(boat.surfacingProgress * Math.PI) * 0.5})`;
          ctx!.fillRect(sx + ps * 0.3, sy + ps, ps * 0.5, ps * 0.5);
          ctx!.fillRect(sx + ps * 0.3, sy + ps * 2.5, ps * 0.5, ps * 0.5);
          // Splash ripples
          ctx!.fillStyle = `rgba(180, 200, 230, ${Math.sin(boat.surfacingProgress * Math.PI) * 0.4})`;
          ctx!.fillRect(sx - ps * 3, sy + ps * 4, ps * 8, ps);
          ctx!.fillRect(sx - ps * 2, sy + ps * 5, ps * 6, ps * 0.5);
        }
      }
    }

    function draw(time: number) {
      if (time - lastAstronomyRef.current > 60_000) {
        recomputeAstronomy(new Date());
        lastAstronomyRef.current = time;
      }
      const w = W(), h = H();
      ctx!.clearRect(0, 0, w, h);
      const bandH = h / 6;
      const pixSize = 4;

      // ── Sky bands ──
      for (let band = 0; band < 6; band++) {
        const color = currentSkyColors[band];
        const y0 = band * bandH, y1 = (band + 1) * bandH;
        ctx!.fillStyle = rgb(color);
        for (let py = y0; py < y1; py += pixSize) ctx!.fillRect(0, Math.floor(py), w, pixSize);
        if (band > 0) {
          ctx!.fillStyle = rgba(lerpColor(currentSkyColors[band - 1], color, 0.5), 0.4);
          ctx!.fillRect(0, Math.floor(y0) - 1, w, 2);
        }
      }

      // ── Stars ──
      const reduced = reducedActivityRef.current;
      if (currentStarOpacity > 0) {
        for (const star of starsRef.current) {
          const tw = reduced ? 0.5 : Math.sin(time / 1000 * star.twinkleSpeed + star.twinklePhase);
          const raw = (tw + 1) / 2;
          const stepped = raw < 0.33 ? 0.2 : raw < 0.66 ? 0.5 : 1.0;
          ctx!.fillStyle = `rgba(255,255,255,${stepped * currentStarOpacity})`;
          const sx = star.x * w, sy = star.y * h, sz = star.size * 2;
          ctx!.fillRect(Math.floor(sx / 2) * 2, Math.floor(sy / 2) * 2, sz, sz);
        }
      }

      // ── Shooting star ──
      const shoot = shootingRef.current;
      if (shoot.active && !reduced) {
        shoot.progress += 0.015;
        if (shoot.progress >= 1) { shoot.active = false; nextShootRef.current = time + 60000 + Math.random() * 180000; }
        else {
          const sx = shoot.x * w + Math.cos(shoot.angle) * shoot.progress * w * 0.3;
          const sy = shoot.y * h + Math.sin(shoot.angle) * shoot.progress * h * 0.3;
          const tail = 30 * (1 - shoot.progress);
          for (let i = 0; i < 8; i++) {
            const f = i / 8;
            ctx!.fillStyle = `rgba(255,255,255,${(1 - f) * 0.9})`;
            ctx!.fillRect(Math.floor(sx - Math.cos(shoot.angle) * f * tail), Math.floor(sy - Math.sin(shoot.angle) * f * tail), 3 - Math.floor(f * 2), 3 - Math.floor(f * 2));
          }
        }
      } else if (time > nextShootRef.current) {
        shootingRef.current = { x: 0.1 + Math.random() * 0.6, y: 0.05 + Math.random() * 0.25, angle: 0.3 + Math.random() * 0.5, progress: 0, active: true };
      }

      // ── Sun ──
      if (currentSunAlt > -3) {
        const azD = (currentSunAz * 180) / Math.PI;
        const sx = ((azD - 90) / 180) * w * 0.6 + w * 0.2;
        const sy = Math.max(0, (1 - currentSunAlt / 90)) * h * 0.7;
        const sp = currentSunAlt > 10 ? SUN_SPRITES.high : SUN_SPRITES.low;
        const sc = currentSunAlt > 10 ? SUN_COLORS.high : SUN_COLORS.low;
        const ps = 5;
        if (currentSunAlt > 0) { for (let r = 40; r > 0; r -= 6) { ctx!.fillStyle = `rgba(255,200,80,${0.03 * (1 - r / 40)})`; ctx!.fillRect(sx - r, sy - r, r * 2, r * 2); } }
        const sw = sp[0].length * ps, sh = sp.length * ps;
        for (let r = 0; r < sp.length; r++) for (let c = 0; c < sp[r].length; c++) { const v = sp[r][c]; if (v > 0) { ctx!.fillStyle = sc[v]; ctx!.fillRect(Math.floor(sx - sw / 2 + c * ps), Math.floor(sy - sh / 2 + r * ps), ps, ps); } }
      }

      // ── Moon ──
      if (currentMoonAlt > -5 && currentMoonIllum.fraction > 0.02) {
        const azD = (currentMoonAz * 180) / Math.PI;
        const mx = ((azD - 90) / 180) * w * 0.6 + w * 0.2;
        const my = Math.max(0, (1 - currentMoonAlt / 90)) * h * 0.7;
        const sp = MOON_SPRITES[getMoonPhaseIndex(currentMoonIllum.phaseValue)];
        const ps = 3;
        const tw = sp[0].length * ps, th = sp.length * ps;
        if (isMoonFullyVisible(mx, my, Math.max(tw, th))) {
          for (let r = 24; r > 0; r -= 5) { ctx!.fillStyle = `rgba(200,200,230,${0.02 * (1 - r / 24)})`; ctx!.fillRect(mx - r, my - r, r * 2, r * 2); }
          for (let r = 0; r < sp.length; r++) for (let c = 0; c < sp[r].length; c++) {
            if (sp[r][c] === 1) {
              ctx!.fillStyle = currentMoonIllum.fraction > 0.5 ? `rgba(240,235,245,${0.8 + Math.sin(time / 2000) * 0.1})` : "rgba(230,225,240,0.85)";
              ctx!.fillRect(Math.floor(mx - tw / 2 + c * ps), Math.floor(my - th / 2 + r * ps), ps, ps);
            }
          }
        }
      }

      // ── Water ──
      const waterH = h * WATER_HEIGHT_FRACTION;
      const waterY = h - waterH;
      const pixW = 4;
      const wbc = currentSkyColors[5];
      const wb = [40, 70, 120];
      ctx!.fillStyle = rgb(lerpColor(wb, wbc, 0.3));
      ctx!.fillRect(0, waterY, w, waterH);

      if (!reduced) {
        for (const wp of waterPixelsRef.current) {
          const sh = Math.sin(time / 1000 * wp.speed + wp.phase);
          const br = Math.max(0, Math.min(1, wp.baseBrightness + sh * 0.15));
          ctx!.fillStyle = rgba(lerpColor(wb, wbc, br * 0.5), 0.5 + br * 0.3);
          ctx!.fillRect(wp.x * pixW, waterY + wp.y * pixW, pixW, pixW);
        }
      }

      // Waves
      for (let x = 0; x < w; x += 8) { ctx!.fillStyle = rgba([180,200,230], 0.3); ctx!.fillRect(x, Math.floor(waterY + 3 + Math.sin(time / 500 + x / 20) * 2), 4, 1); }
      for (let x = 4; x < w; x += 10) { ctx!.fillStyle = rgba([160,190,220], 0.2); ctx!.fillRect(x, Math.floor(waterY + 8 + Math.sin(time / 700 + x / 15) * 1.5), 3, 1); }

      // ── Seaweed ──
      for (const sw of seaweedRef.current) {
        const bx = sw.x * w;
        const segs = Math.floor(sw.height / 6);
        for (let i = 0; i < segs; i++) {
          const sway = reduced ? 0 : Math.sin(time / 1000 * sw.swaySpeed + sw.swayPhase + i * 0.3) * (i * 1.5);
          const sy = waterY + waterH - i * 6;
          if (sy < waterY) break;
          ctx!.fillStyle = sw.color;
          ctx!.fillRect(Math.floor(bx + sway), Math.floor(sy), 4, 6);
        }
      }

      // ── Fish (4 shape variants) ──
      for (const f of fishRef.current) {
        if (!reduced) { f.x += f.speed; if (f.x > 1.1) f.x = -0.1; }
        const fx = f.x * w;
        const bob = Math.sin(time / 800 + f.bobPhase) * 3;
        const fy = waterY + waterH * 0.3 + f.y * waterH * 0.5 + bob;
        FISH_DRAWERS[f.shape](ctx!, fx, fy, f.size, f.color);
      }

      // ── Night factor for island/boat visibility ──
      const nightFactor = Math.max(0, Math.min(1, (-currentSunAlt) / 18));

      // ── Bikini Bottom island (right side) ──
      drawIsland(w, waterY, waterH, nightFactor);

      // ── Tyrion's boat (left side) ──
      drawBoat(w, waterY, waterH, time, nightFactor, reduced);

      animFrameRef.current = requestAnimationFrame(draw);
    }

    animFrameRef.current = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(animFrameRef.current); window.removeEventListener("resize", resize); };
  }, [now]);

  return (
    <canvas ref={canvasRef} className="fixed inset-0 -z-10" style={{ imageRendering: "pixelated" }} aria-hidden="true" />
  );
}
