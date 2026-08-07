/**
 * Live Tehran Sky Background — Pixel-Art Canvas Renderer
 *
 * A living backdrop that follows the real astronomical state of Tehran's sky.
 * Uses SunCalc3 for accurate sun/moon positions and illumination.
 *
 * Renders pixel-art style: discrete sky bands, blocky sun/moon sprites,
 * pixel stars with stepped twinkle, shooting star streaks, animated
 * water with seaweed and fish — all on a <canvas> for performance.
 *
 * IMPORTANT: SunCalc needs a real, correct Date (absolute point in time).
 * Do NOT shift/reformat the Date object.
 */

import { useEffect, useRef, useState } from "react";
import SunCalc from "suncalc3";

// ── Tehran coordinates ──────────────────────────────────────────────────────
const TEHRAN_LAT = 35.6892;
const TEHRAN_LON = 51.3890;

// ── Water height ────────────────────────────────────────────────────────────
const WATER_HEIGHT_FRACTION = 0.40; // 40% of screen for water

// ── Color helpers ───────────────────────────────────────────────────────────
function lerpColor(a: number[], b: number[], t: number): number[] {
  return a.map((v, i) => Math.round(v + (b[i] - v) * t));
}

function rgb(c: number[]): string {
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

function rgba(c: number[], a: number): string {
  return `rgba(${c[0]},${c[1]},${c[2]},${a})`;
}

// ── Sky palette definitions ─────────────────────────────────────────────────
const SKY_PALETTES = {
  nightDeep: [
    [8, 10, 26], [12, 16, 35], [16, 18, 42],
    [18, 14, 50], [20, 12, 45], [14, 10, 30],
  ],
  nightLight: [
    [14, 18, 38], [20, 24, 52], [28, 22, 58],
    [35, 22, 55], [40, 20, 50], [28, 18, 40],
  ],
  dusk: [
    [35, 28, 65], [65, 35, 70], [110, 50, 65],
    [180, 80, 60], [200, 110, 60], [150, 80, 50],
  ],
  golden: [
    [70, 110, 170], [120, 160, 210], [190, 190, 180],
    [240, 180, 100], [255, 200, 120], [240, 170, 90],
  ],
  day: [
    [60, 120, 200], [100, 160, 220], [140, 190, 235],
    [180, 215, 245], [210, 230, 250], [190, 215, 235],
  ],
  dayBright: [
    [40, 100, 190], [70, 140, 220], [110, 180, 240],
    [150, 205, 245], [185, 225, 250], [170, 215, 245],
  ],
};

function getSkyColors(sunAlt: number): number[][] {
  let from: number[][];
  let to: number[][];
  let t: number;

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
  high: [
    [0,0,2,2,2,2,0,0], [0,2,1,1,1,1,2,0],
    [2,1,1,2,2,1,1,2], [2,1,2,1,1,2,1,2],
    [2,1,2,1,1,2,1,2], [2,1,1,2,2,1,1,2],
    [0,2,1,1,1,1,2,0], [0,0,2,2,2,2,0,0],
  ],
  low: [
    [0,0,3,3,3,3,0,0], [0,3,4,3,3,4,3,0],
    [3,4,3,3,3,3,4,3], [3,3,3,4,4,3,3,3],
    [3,3,3,4,4,3,3,3], [3,4,3,3,3,3,4,3],
    [0,3,4,3,3,4,3,0], [0,0,3,3,3,3,0,0],
  ],
};
const SUN_COLORS = {
  high: ["", "#FFF8E1", "#FFD54F", "#FFB300", ""],
  low: ["", "#FF6644", "#FF8C42", "#CC4422", "#993311"],
};

// ── Moon sprites (10x10 for 8 phases) ───────────────────────────────────────
const MOON_SPRITES: number[][][] = [
  // 0: New
  Array.from({ length: 10 }, () => [0,0,0,0,0,0,0,0,0,0]),
  // 1: Waxing crescent
  [[0,0,0,0,0,0,0,1,1,0],[0,0,0,0,0,0,1,1,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,0,0,0],[0,0,0,0,0,0,1,1,0,0],[0,0,0,0,0,0,0,1,1,0]],
  // 2: First quarter
  [[0,0,0,0,0,1,1,1,1,0],[0,0,0,0,0,1,1,1,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,0,0,0],[0,0,0,0,0,1,1,1,0,0],[0,0,0,0,0,1,1,1,1,0]],
  // 3: Waxing gibbous
  [[0,0,0,1,1,1,1,1,1,0],[0,0,1,1,1,1,1,1,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,1,1,1,1,1,1,0,0,0],[0,0,1,1,1,1,1,1,0,0],[0,0,0,1,1,1,1,1,1,0]],
  // 4: Full
  [[0,0,1,1,1,1,1,1,0,0],[0,1,1,1,1,1,1,1,1,0],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,1,0],[0,0,1,1,1,1,1,1,0,0]],
  // 5: Waning gibbous
  [[0,0,1,1,1,1,1,0,0,0],[0,0,1,1,1,1,1,1,0,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,0,1,1,1,1,1,1,0],[0,0,1,1,1,1,1,1,0,0],[0,0,1,1,1,1,1,0,0,0]],
  // 6: Last quarter
  [[0,1,1,1,1,0,0,0,0,0],[0,0,1,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,0,1,1,0,0,0,0,0],[0,0,1,1,1,0,0,0,0,0],[0,1,1,1,1,0,0,0,0,0]],
  // 7: Waning crescent
  [[0,1,1,0,0,0,0,0,0,0],[0,0,1,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,0,1,0,0,0,0,0,0],[0,0,1,1,0,0,0,0,0,0],[0,1,1,0,0,0,0,0,0,0]],
];

function getMoonPhaseIndex(phaseValue: number): number {
  return Math.round(phaseValue * 8) % 8;
}

// ── Stars ───────────────────────────────────────────────────────────────────
interface Star { x: number; y: number; size: number; twinklePhase: number; twinkleSpeed: number; }

function generateStars(count: number): Star[] {
  const stars: Star[] = [];
  for (let i = 0; i < count; i++) {
    stars.push({
      x: Math.random(), y: Math.random() * 0.65,
      size: Math.random() > 0.7 ? 2 : 1,
      twinklePhase: Math.random() * Math.PI * 2,
      twinkleSpeed: 1.5 + Math.random() * 3,
    });
  }
  return stars;
}

// ── Shooting star ───────────────────────────────────────────────────────────
interface ShootingStar { x: number; y: number; angle: number; progress: number; active: boolean; }

// ── Seaweed ─────────────────────────────────────────────────────────────────
interface Seaweed { x: number; height: number; swaySpeed: number; swayPhase: number; color: string; }

function generateSeaweed(count: number): Seaweed[] {
  const greens = ["#2D5A27", "#3A7A33", "#1E4D1A", "#4A8A40", "#256B1F"];
  const seaweeds: Seaweed[] = [];
  for (let i = 0; i < count; i++) {
    seaweeds.push({
      x: Math.random(),
      height: 30 + Math.random() * 50,
      swaySpeed: 0.8 + Math.random() * 1.5,
      swayPhase: Math.random() * Math.PI * 2,
      color: greens[Math.floor(Math.random() * greens.length)],
    });
  }
  return seaweeds;
}

// ── Fish ────────────────────────────────────────────────────────────────────
interface Fish { x: number; y: number; speed: number; size: number; color: string; bobPhase: number; }

function generateFish(count: number): Fish[] {
  const colors = ["#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF", "#FF8FB1"];
  const fish: Fish[] = [];
  for (let i = 0; i < count; i++) {
    fish.push({
      x: Math.random(),
      y: Math.random(),
      speed: 0.0003 + Math.random() * 0.0005,
      size: 3 + Math.floor(Math.random() * 3),
      color: colors[Math.floor(Math.random() * colors.length)],
      bobPhase: Math.random() * Math.PI * 2,
    });
  }
  return fish;
}

// ── Water pixels ────────────────────────────────────────────────────────────
interface WaterPixel { x: number; y: number; baseBrightness: number; phase: number; speed: number; }

function generateWaterPixels(cols: number, rows: number): WaterPixel[] {
  const pixels: WaterPixel[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      pixels.push({
        x: c, y: r,
        baseBrightness: 0.3 + Math.random() * 0.4,
        phase: Math.random() * Math.PI * 2,
        speed: 1 + Math.random() * 2,
      });
    }
  }
  return pixels;
}

// ── Draw a pixel-art fish on canvas ─────────────────────────────────────────
function drawFish(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, color: string, facingLeft: boolean) {
  const s = size;
  ctx.fillStyle = color;
  // Body (oval)
  ctx.fillRect(x + s, y, s * 3, s);
  ctx.fillRect(x, y + s, s * 5, s);
  ctx.fillRect(x + s, y + s * 2, s * 3, s);
  // Tail
  if (facingLeft) {
    ctx.fillRect(x + s * 4, y - s, s, s);
    ctx.fillRect(x + s * 4, y + s * 2, s, s);
  } else {
    ctx.fillRect(x - s, y - s, s, s);
    ctx.fillRect(x - s, y + s * 2, s, s);
  }
  // Eye
  ctx.fillStyle = "#FFFFFF";
  const eyeX = facingLeft ? x + s * 3 : x + s;
  ctx.fillRect(eyeX, y + s * 0.5, s * 0.8, s * 0.8);
  ctx.fillStyle = "#1A1A2E";
  ctx.fillRect(eyeX + s * 0.2, y + s * 0.6, s * 0.4, s * 0.4);
}

// ── Component ───────────────────────────────────────────────────────────────
export default function LiveSkyBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [now, setNow] = useState(() => new Date());
  const starsRef = useRef<Star[]>(generateStars(100));
  const seaweedRef = useRef<Seaweed[]>(generateSeaweed(12));
  const fishRef = useRef<Fish[]>(generateFish(4));
  const shootingRef = useRef<ShootingStar>({ x: 0, y: 0, angle: 0, progress: 0, active: false });
  const nextShootRef = useRef(Date.now() + 60000 + Math.random() * 180000);
  const animFrameRef = useRef<number>(0);
  const waterPixelsRef = useRef<WaterPixel[]>([]);
  const lastAstronomyRef = useRef(0); // last time we recomputed sun/moon

  // Recompute astronomical data every 60 seconds (lightweight, no full re-setup)
  useEffect(() => {
    const iv = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(iv);
  }, []);

  // Animation loop — runs once, re-reads `now` inside the loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // ── Astronomy state (recomputed periodically inside the loop) ──
    let currentSunAlt = 0;
    let currentSunAz = 0;
    let currentMoonAlt = 0;
    let currentMoonAz = 0;
    let currentMoonIllum = { fraction: 0, phaseValue: 0, angle: 0 };
    let currentIsNight = false;
    let currentIsDusk = false;
    let currentStarOpacity = 0;
    let currentSkyColors = SKY_PALETTES.nightDeep;

    function recomputeAstronomy(dateNow: Date) {
      const sunPos = SunCalc.getPosition(dateNow, TEHRAN_LAT, TEHRAN_LON);
      currentSunAlt = (sunPos.altitude * 180) / Math.PI;
      currentSunAz = sunPos.azimuth + Math.PI;
      const moonPos = SunCalc.getMoonPosition(dateNow, TEHRAN_LAT, TEHRAN_LON);
      currentMoonIllum = SunCalc.getMoonIllumination(dateNow) as any;
      currentMoonAlt = (moonPos.altitude * 180) / Math.PI;
      currentMoonAz = moonPos.azimuth + Math.PI;
      currentIsNight = currentSunAlt < -6;
      currentIsDusk = currentSunAlt >= -6 && currentSunAlt < 0;
      currentStarOpacity = currentIsNight ? 1 : currentIsDusk ? Math.min(1, (-currentSunAlt) / 6) : 0;
      currentSkyColors = getSkyColors(currentSunAlt);
    }

    // Initial computation
    recomputeAstronomy(new Date());

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.setTransform(1, 0, 0, 1, 0, 0); // RESET transform before re-scaling
      ctx.scale(dpr, dpr);
      const cols = Math.ceil(window.innerWidth / 4);
      const rows = Math.ceil((window.innerHeight * WATER_HEIGHT_FRACTION) / 4);
      waterPixelsRef.current = generateWaterPixels(cols, rows);
    };
    resize();
    window.addEventListener("resize", resize);

    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    // ── Moon bounds check — prevent partial rendering at canvas edges ──
    function isMoonFullyVisible(mx: number, my: number, spriteSize: number): boolean {
      const margin = spriteSize * 0.5;
      return mx > margin && mx < W() - margin && my > margin && my < H() - margin;
    }

    function draw(time: number) {
      // Recompute astronomy every 60 seconds inside the persistent loop
      if (time - lastAstronomyRef.current > 60_000) {
        recomputeAstronomy(new Date());
        lastAstronomyRef.current = time;
      }

      const w = W();
      const h = H();
      ctx!.clearRect(0, 0, w, h);
      const bandH = h / 6;
      const pixSize = 4;

      // ── Sky bands ──
      for (let band = 0; band < 6; band++) {
        const color = currentSkyColors[band];
        const y0 = band * bandH;
        const y1 = (band + 1) * bandH;
        ctx!.fillStyle = rgb(color);
        for (let py = y0; py < y1; py += pixSize) {
          ctx!.fillRect(0, Math.floor(py), w, pixSize);
        }
        if (band > 0) {
          ctx!.fillStyle = rgba(lerpColor(currentSkyColors[band - 1], color, 0.5), 0.4);
          ctx!.fillRect(0, Math.floor(y0) - 1, w, 2);
        }
      }

      // ── Stars ──
      if (currentStarOpacity > 0) {
        for (const star of starsRef.current) {
          const twinkle = Math.sin(time / 1000 * star.twinkleSpeed + star.twinklePhase);
          const rawAlpha = (twinkle + 1) / 2;
          const stepped = rawAlpha < 0.33 ? 0.2 : rawAlpha < 0.66 ? 0.5 : 1.0;
          ctx!.fillStyle = `rgba(255, 255, 255, ${stepped * currentStarOpacity})`;
          const sx = star.x * w;
          const sy = star.y * h;
          const size = star.size * 2;
          ctx!.fillRect(Math.floor(sx / 2) * 2, Math.floor(sy / 2) * 2, size, size);
        }
      }

      // ── Shooting star ──
      const shoot = shootingRef.current;
      if (shoot.active) {
        shoot.progress += 0.015;
        if (shoot.progress >= 1) {
          shoot.active = false;
          nextShootRef.current = time + 60000 + Math.random() * 180000;
        } else {
          const sx = shoot.x * w + Math.cos(shoot.angle) * shoot.progress * w * 0.3;
          const sy = shoot.y * h + Math.sin(shoot.angle) * shoot.progress * h * 0.3;
          const tailLen = 30 * (1 - shoot.progress);
          for (let i = 0; i < 8; i++) {
            const frac = i / 8;
            const px = sx - Math.cos(shoot.angle) * frac * tailLen;
            const py = sy - Math.sin(shoot.angle) * frac * tailLen;
            ctx!.fillStyle = `rgba(255, 255, 255, ${(1 - frac) * 0.9})`;
            ctx!.fillRect(Math.floor(px), Math.floor(py), 3 - Math.floor(frac * 2), 3 - Math.floor(frac * 2));
          }
        }
      } else if (time > nextShootRef.current) {
        shootingRef.current = { x: 0.1 + Math.random() * 0.6, y: 0.05 + Math.random() * 0.25, angle: 0.3 + Math.random() * 0.5, progress: 0, active: true };
      }

      // ── Sun ──
      const showSun = currentSunAlt > -3;
      if (showSun) {
        const azDeg = (currentSunAz * 180) / Math.PI;
        const sx = ((azDeg - 90) / 180) * w * 0.6 + w * 0.2;
        const sy = Math.max(0, (1 - currentSunAlt / 90)) * h * 0.7;
        const sprite = currentSunAlt > 10 ? SUN_SPRITES.high : SUN_SPRITES.low;
        const colors = currentSunAlt > 10 ? SUN_COLORS.high : SUN_COLORS.low;
        const pixelSize = 5;
        if (currentSunAlt > 0) {
          for (let r = 40; r > 0; r -= 6) {
            ctx!.fillStyle = `rgba(255, 200, 80, ${0.03 * (1 - r / 40)})`;
            ctx!.fillRect(sx - r, sy - r, r * 2, r * 2);
          }
        }
        const spriteW = sprite[0].length * pixelSize;
        const spriteH = sprite.length * pixelSize;
        const ox = sx - spriteW / 2;
        const oy = sy - spriteH / 2;
        for (let row = 0; row < sprite.length; row++) {
          for (let col = 0; col < sprite[row].length; col++) {
            const c = sprite[row][col];
            if (c > 0) {
              ctx!.fillStyle = colors[c];
              ctx!.fillRect(Math.floor(ox + col * pixelSize), Math.floor(oy + row * pixelSize), pixelSize, pixelSize);
            }
          }
        }
      }

      // ── Moon ──
      const showMoon = currentMoonAlt > -5 && currentMoonIllum.fraction > 0.02;
      if (showMoon) {
        const azDeg = (currentMoonAz * 180) / Math.PI;
        const mx = ((azDeg - 90) / 180) * w * 0.6 + w * 0.2;
        const my = Math.max(0, (1 - currentMoonAlt / 90)) * h * 0.7;
        const phaseIdx = getMoonPhaseIndex(currentMoonIllum.phaseValue);
        const sprite = MOON_SPRITES[phaseIdx];
        const pixelSize = 3;
        const totalW = sprite[0].length * pixelSize;
        const totalH = sprite.length * pixelSize;

        // FIX: only draw if fully visible (prevents stray bracket artifacts)
        if (!isMoonFullyVisible(mx, my, Math.max(totalW, totalH))) {
          // Skip rendering — moon is too close to edge, would be partially cropped
        } else {
          for (let r = 24; r > 0; r -= 5) {
            ctx!.fillStyle = `rgba(200, 200, 230, ${0.02 * (1 - r / 24)})`;
            ctx!.fillRect(mx - r, my - r, r * 2, r * 2);
          }
          const ox = mx - totalW / 2;
          const oy = my - totalH / 2;
          for (let row = 0; row < sprite.length; row++) {
            for (let col = 0; col < sprite[row].length; col++) {
              if (sprite[row][col] === 1) {
                const lit = currentMoonIllum.fraction > 0.5
                  ? `rgba(240, 235, 245, ${0.8 + Math.sin(time / 2000) * 0.1})`
                  : "rgba(230, 225, 240, 0.85)";
                ctx!.fillStyle = lit;
                ctx!.fillRect(Math.floor(ox + col * pixelSize), Math.floor(oy + row * pixelSize), pixelSize, pixelSize);
              }
            }
          }
        }
      }

      // ── Water (pixel-art, 40% of screen) ──
      const waterH = h * WATER_HEIGHT_FRACTION;
      const waterY = h - waterH;
      const pixW = 4;
      const waterBaseColor = currentSkyColors[5];

      // Fill base water background
      const waterBlue = [40, 70, 120];
      ctx!.fillStyle = rgb(lerpColor(waterBlue, waterBaseColor, 0.3));
      ctx!.fillRect(0, waterY, w, waterH);

      // Shimmer pixels
      for (const wp of waterPixelsRef.current) {
        const shimmer = Math.sin(time / 1000 * wp.speed + wp.phase);
        const bright = wp.baseBrightness + shimmer * 0.15;
        const clamped = Math.max(0, Math.min(1, bright));
        const mixed = lerpColor(waterBlue, waterBaseColor, clamped * 0.5);
        ctx!.fillStyle = rgba(mixed, 0.5 + clamped * 0.3);
        ctx!.fillRect(wp.x * pixW, waterY + wp.y * pixW, pixW, pixW);
      }

      // Wave lines
      for (let x = 0; x < w; x += 8) {
        const waveY = waterY + 3 + Math.sin(time / 500 + x / 20) * 2;
        ctx!.fillStyle = rgba([180, 200, 230], 0.3);
        ctx!.fillRect(x, Math.floor(waveY), 4, 1);
      }
      // Second wave row
      for (let x = 4; x < w; x += 10) {
        const waveY2 = waterY + 8 + Math.sin(time / 700 + x / 15) * 1.5;
        ctx!.fillStyle = rgba([160, 190, 220], 0.2);
        ctx!.fillRect(x, Math.floor(waveY2), 3, 1);
      }

      // ── Seaweed ──
      for (const sw of seaweedRef.current) {
        const baseX = sw.x * w;
        const segments = Math.floor(sw.height / 6);
        for (let i = 0; i < segments; i++) {
          const sway = Math.sin(time / 1000 * sw.swaySpeed + sw.swayPhase + i * 0.3) * (i * 1.5);
          const segY = waterY + waterH - i * 6;
          if (segY < waterY) break;
          ctx!.fillStyle = sw.color;
          ctx!.fillRect(Math.floor(baseX + sway), Math.floor(segY), 4, 6);
        }
      }

      // ── Fish ──
      for (const f of fishRef.current) {
        // Move fish
        f.x += f.speed;
        if (f.x > 1.1) f.x = -0.1;
        const fishX = f.x * w;
        const bob = Math.sin(time / 800 + f.bobPhase) * 3;
        const fishY = waterY + waterH * 0.3 + f.y * waterH * 0.5 + bob;
        drawFish(ctx!, fishX, fishY, f.size, f.color, false);
      }

      animFrameRef.current = requestAnimationFrame(draw);
    }

    animFrameRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener("resize", resize);
    };
  }, [now]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 -z-10"
      style={{ imageRendering: "pixelated" }}
      aria-hidden="true"
    />
  );
}
