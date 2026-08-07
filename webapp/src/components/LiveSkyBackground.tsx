/**
 * Live Tehran Sky Background — Pixel-Art Canvas Renderer
 *
 * A living backdrop that follows the real astronomical state of Tehran's sky.
 * Uses SunCalc3 for accurate sun/moon positions and illumination.
 *
 * Renders pixel-art style: discrete sky bands, blocky sun/moon sprites,
 * pixel stars with stepped twinkle, shooting star streaks, and animated
 * water reflection — all on a <canvas> for performance.
 *
 * IMPORTANT: SunCalc needs a real, correct Date (absolute point in time).
 * Do NOT shift/reformat the Date object — `new Date()` already represents
 * the correct instant in UTC regardless of the visitor's local timezone.
 * Tehran's offset is only needed for DISPLAY purposes.
 */

import { useEffect, useRef, useState } from "react";
import SunCalc from "suncalc3";

// ── Tehran coordinates ──────────────────────────────────────────────────────
const TEHRAN_LAT = 35.6892;
const TEHRAN_LON = 51.3890;

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
// Each palette is 6 bands from top to bottom, as RGB arrays
const SKY_PALETTES = {
  // Deep night (sun < -18°)
  nightDeep: [
    [8, 10, 26],      // top: near-black
    [12, 16, 35],     // deep navy
    [16, 18, 42],     // dark blue
    [18, 14, 50],     // hint of purple
    [20, 12, 45],     // purple-navy
    [14, 10, 30],     // bottom
  ],
  // Astronomical twilight (-18 to -12)
  nightLight: [
    [14, 18, 38],     // deep navy
    [20, 24, 52],     // navy
    [28, 22, 58],     // purple-blue
    [35, 22, 55],     // purple
    [40, 20, 50],     // warm purple
    [28, 18, 40],     // bottom
  ],
  // Nautical twilight (-12 to -6)
  dusk: [
    [35, 28, 65],     // purple sky
    [65, 35, 70],     // magenta-purple
    [110, 50, 65],    // warm magenta
    [180, 80, 60],    // orange-pink
    [200, 110, 60],   // orange
    [150, 80, 50],    // warm brown-orange
  ],
  // Civil twilight / golden hour (-6 to 0)
  golden: [
    [70, 110, 170],   // blue
    [120, 160, 210],  // light blue
    [190, 190, 180],  // warm grey
    [240, 180, 100],  // golden
    [255, 200, 120],  // bright gold
    [240, 170, 90],   // amber
  ],
  // Day (sun > 0°)
  day: [
    [60, 120, 200],   // sky blue
    [100, 160, 220],  // lighter blue
    [140, 190, 235],  // pale blue
    [180, 215, 245],  // very light blue
    [210, 230, 250],  // near white-blue
    [190, 215, 235],  // horizon haze
  ],
  // Bright day (sun at zenith)
  dayBright: [
    [40, 100, 190],   // rich sky blue
    [70, 140, 220],   // medium blue
    [110, 180, 240],  // light blue
    [150, 205, 245],  // pale blue
    [185, 225, 250],  // near white
    [170, 215, 245],  // horizon
  ],
};

// Interpolate between palette bands based on sun altitude
function getSkyColors(sunAlt: number): number[][] {
  const bands = 6;
  let from: number[][];
  let to: number[][];
  let t: number;

  if (sunAlt < -18) {
    return SKY_PALETTES.nightDeep;
  } else if (sunAlt < -12) {
    from = SKY_PALETTES.nightDeep;
    to = SKY_PALETTES.nightLight;
    t = (sunAlt + 18) / 6;
  } else if (sunAlt < -6) {
    from = SKY_PALETTES.nightLight;
    to = SKY_PALETTES.dusk;
    t = (sunAlt + 12) / 6;
  } else if (sunAlt < 0) {
    from = SKY_PALETTES.dusk;
    to = SKY_PALETTES.golden;
    t = (sunAlt + 6) / 6;
  } else if (sunAlt < 45) {
    from = SKY_PALETTES.golden;
    to = SKY_PALETTES.day;
    t = sunAlt / 45;
  } else {
    from = SKY_PALETTES.day;
    to = SKY_PALETTES.dayBright;
    t = (sunAlt - 45) / 45;
  }

  t = Math.max(0, Math.min(1, t));
  const result: number[][] = [];
  for (let i = 0; i < bands; i++) {
    result.push(lerpColor(from[i], to[i], t));
  }
  return result;
}

// ── Pixel-art sun sprite (8x8) ─────────────────────────────────────────────
// Colors: 0=transparent, 1=core white, 2=bright yellow, 3=orange, 4=red(dusk)
const SUN_SPRITES = {
  // High sun (yellow-white)
  high: [
    [0, 0, 2, 2, 2, 2, 0, 0],
    [0, 2, 1, 1, 1, 1, 2, 0],
    [2, 1, 1, 2, 2, 1, 1, 2],
    [2, 1, 2, 1, 1, 2, 1, 2],
    [2, 1, 2, 1, 1, 2, 1, 2],
    [2, 1, 1, 2, 2, 1, 1, 2],
    [0, 2, 1, 1, 1, 1, 2, 0],
    [0, 0, 2, 2, 2, 2, 0, 0],
  ],
  // Low sun (orange-red, near horizon)
  low: [
    [0, 0, 3, 3, 3, 3, 0, 0],
    [0, 3, 4, 3, 3, 4, 3, 0],
    [3, 4, 3, 3, 3, 3, 4, 3],
    [3, 3, 3, 4, 4, 3, 3, 3],
    [3, 3, 3, 4, 4, 3, 3, 3],
    [3, 4, 3, 3, 3, 3, 4, 3],
    [0, 3, 4, 3, 3, 4, 3, 0],
    [0, 0, 3, 3, 3, 3, 0, 0],
  ],
};

const SUN_COLORS = {
  high: ["", "#FFF8E1", "#FFD54F", "#FFB300", ""],
  low: ["", "#FF6644", "#FF8C42", "#CC4422", "#993311"],
};

// ── Pixel-art moon sprites (10x10 for 8 phases) ─────────────────────────────
// phase index: 0=new, 1=waxing crescent, 2=first quarter, 3=waxing gibbous,
// 4=full, 5=waning gibbous, 6=last quarter, 7=waning crescent
const MOON_SPRITES: number[][][] = [
  // 0: New moon (all dark)
  Array.from({ length: 10 }, () => [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
  // 1: Waxing crescent (right sliver lit)
  [
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
  ],
  // 2: First quarter (right half lit)
  [
    [0, 0, 0, 0, 0, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 1, 1, 0],
  ],
  // 3: Waxing gibbous (most lit, left sliver dark)
  [
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
  ],
  // 4: Full moon (all lit)
  [
    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
  ],
  // 5: Waning gibbous (most lit, right sliver dark)
  [
    [0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
  ],
  // 6: Last quarter (left half lit)
  [
    [0, 1, 1, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 0, 0, 0, 0, 0],
  ],
  // 7: Waning crescent (left sliver lit)
  [
    [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
  ],
];

function getMoonPhaseIndex(phase: number): number {
  // phase: 0=new, 0.25=first quarter, 0.5=full, 0.75=last quarter, 1=new
  const idx = Math.round(phase * 8) % 8;
  return idx;
}

// ── Stars ───────────────────────────────────────────────────────────────────
interface Star {
  x: number;
  y: number;
  size: number; // 1 or 2 pixels
  twinklePhase: number;
  twinkleSpeed: number;
}

function generateStars(count: number): Star[] {
  const stars: Star[] = [];
  for (let i = 0; i < count; i++) {
    stars.push({
      x: Math.random(),
      y: Math.random() * 0.65, // upper 65%
      size: Math.random() > 0.7 ? 2 : 1,
      twinklePhase: Math.random() * Math.PI * 2,
      twinkleSpeed: 1.5 + Math.random() * 3,
    });
  }
  return stars;
}

// ── Shooting star ───────────────────────────────────────────────────────────
interface ShootingStar {
  x: number;
  y: number;
  angle: number;
  speed: number;
  length: number;
  progress: number; // 0 to 1
  active: boolean;
}

// ── Water shimmer pixels ────────────────────────────────────────────────────
interface WaterPixel {
  x: number;
  y: number;
  baseBrightness: number;
  phase: number;
  speed: number;
}

function generateWaterPixels(w: number, h: number): WaterPixel[] {
  const pixels: WaterPixel[] = [];
  const cols = Math.ceil(w / 4);
  const rows = Math.ceil(h / 4);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      pixels.push({
        x: c,
        y: r,
        baseBrightness: 0.3 + Math.random() * 0.4,
        phase: Math.random() * Math.PI * 2,
        speed: 1 + Math.random() * 2,
      });
    }
  }
  return pixels;
}

// ── Component ───────────────────────────────────────────────────────────────
export default function LiveSkyBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [now, setNow] = useState(() => new Date());
  const starsRef = useRef<Star[]>(generateStars(100));
  const shootingRef = useRef<ShootingStar>({
    x: 0, y: 0, angle: 0, speed: 0, length: 0, progress: 0, active: false,
  });
  const nextShootRef = useRef(Date.now() + 60000 + Math.random() * 180000);
  const animFrameRef = useRef<number>(0);
  const waterPixelsRef = useRef<WaterPixel[]>([]);

  // Recompute astronomical data every 60 seconds
  useEffect(() => {
    const iv = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(iv);
  }, []);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.scale(dpr, dpr);
      waterPixelsRef.current = generateWaterPixels(
        Math.ceil(window.innerWidth / 4),
        Math.ceil(window.innerHeight * 0.18 / 4)
      );
    };
    resize();
    window.addEventListener("resize", resize);

    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    // Sun/moon calculations (use the real Date — SunCalc handles timezone via lat/lon)
    const sunPos = SunCalc.getPosition(now, TEHRAN_LAT, TEHRAN_LON);
    const sunAlt = (sunPos.altitude * 180) / Math.PI;
    const sunAz = sunPos.azimuth + Math.PI; // normalize
    const moonPos = SunCalc.getMoonPosition(now, TEHRAN_LAT, TEHRAN_LON);
    const moonIllum = SunCalc.getMoonIllumination(now);
    const moonAlt = (moonPos.altitude * 180) / Math.PI;
    const moonAz = moonPos.azimuth + Math.PI;

    const isNight = sunAlt < -6;
    const isDusk = sunAlt >= -6 && sunAlt < 0;
    const starOpacity = isNight ? 1 : isDusk ? Math.min(1, (-sunAlt) / 6) : 0;

    // Sun screen position
    const sunScreenX = () => {
      const azDeg = (sunAz * 180) / Math.PI;
      return ((azDeg - 90) / 180) * W() * 0.6 + W() * 0.2;
    };
    const sunScreenY = () => {
      return Math.max(0, (1 - sunAlt / 90)) * H() * 0.7;
    };
    const showSun = sunAlt > -3;

    // Moon screen position
    const moonScreenX = () => {
      const azDeg = (moonAz * 180) / Math.PI;
      return ((azDeg - 90) / 180) * W() * 0.6 + W() * 0.2;
    };
    const moonScreenY = () => {
      return Math.max(0, (1 - moonAlt / 90)) * H() * 0.7;
    };
    const showMoon = moonAlt > -5 && moonIllum.fraction > 0.02;

    const skyColors = getSkyColors(sunAlt);

    function draw(time: number) {
      ctx!.clearRect(0, 0, W(), H());
      const w = W();
      const h = H();
      const bandH = h / 6;
      const pixSize = 4; // pixel block size for sky bands

      // ── Sky bands (pixel-art style) ──
      for (let band = 0; band < 6; band++) {
        const color = skyColors[band];
        const y0 = band * bandH;
        const y1 = (band + 1) * bandH;
        ctx!.fillStyle = rgb(color);
        // Draw as rows of pixel blocks for the pixel-art feel
        for (let py = y0; py < y1; py += pixSize) {
          ctx!.fillRect(0, Math.floor(py), w, pixSize);
        }
        // Add subtle horizontal line between bands for retro feel
        if (band > 0) {
          ctx!.fillStyle = rgba(lerpColor(skyColors[band - 1], color, 0.5), 0.4);
          ctx!.fillRect(0, Math.floor(y0) - 1, w, 2);
        }
      }

      // ── Stars ──
      if (starOpacity > 0) {
        for (const star of starsRef.current) {
          const twinkle = Math.sin(time / 1000 * star.twinkleSpeed + star.twinklePhase);
          // Stepped twinkle: snap to 3 discrete levels for pixel-art feel
          const rawAlpha = (twinkle + 1) / 2; // 0 to 1
          const stepped = rawAlpha < 0.33 ? 0.2 : rawAlpha < 0.66 ? 0.5 : 1.0;
          const alpha = stepped * starOpacity;
          ctx!.fillStyle = `rgba(255, 255, 255, ${alpha})`;
          const sx = star.x * w;
          const sy = star.y * h;
          const size = star.size * 2; // pixel-art sized stars
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
          // Pixel-art streak: blocky line of pixels
          for (let i = 0; i < 8; i++) {
            const frac = i / 8;
            const px = sx - Math.cos(shoot.angle) * frac * tailLen;
            const py = sy - Math.sin(shoot.angle) * frac * tailLen;
            const a = (1 - frac) * 0.9;
            ctx!.fillStyle = `rgba(255, 255, 255, ${a})`;
            const blockSize = 3 - Math.floor(frac * 2);
            ctx!.fillRect(Math.floor(px), Math.floor(py), blockSize, blockSize);
          }
        }
      } else if (time > nextShootRef.current) {
        shootingRef.current = {
          x: 0.1 + Math.random() * 0.6,
          y: 0.05 + Math.random() * 0.25,
          angle: 0.3 + Math.random() * 0.5,
          speed: 1,
          length: 30,
          progress: 0,
          active: true,
        };
      }

      // ── Sun (pixel-art sprite) ──
      if (showSun) {
        const sx = sunScreenX();
        const sy = sunScreenY();
        const sprite = sunAlt > 10 ? SUN_SPRITES.high : SUN_SPRITES.low;
        const colors = sunAlt > 10 ? SUN_COLORS.high : SUN_COLORS.low;
        const pixelSize = 5;

        // Subtle pixel glow behind sun
        if (sunAlt > 0) {
          const glowSize = 40;
          for (let r = glowSize; r > 0; r -= 6) {
            const a = 0.03 * (1 - r / glowSize);
            ctx!.fillStyle = `rgba(255, 200, 80, ${a})`;
            ctx!.fillRect(sx - r, sy - r, r * 2, r * 2);
          }
        }

        // Draw sprite
        const spriteW = sprite[0].length * pixelSize;
        const spriteH = sprite.length * pixelSize;
        const ox = sx - spriteW / 2;
        const oy = sy - spriteH / 2;
        for (let row = 0; row < sprite.length; row++) {
          for (let col = 0; col < sprite[row].length; col++) {
            const c = sprite[row][col];
            if (c > 0) {
              ctx!.fillStyle = colors[c];
              ctx!.fillRect(
                Math.floor(ox + col * pixelSize),
                Math.floor(oy + row * pixelSize),
                pixelSize,
                pixelSize
              );
            }
          }
        }
      }

      // ── Moon (pixel-art sprite with real phase) ──────────────────
      if (showMoon) {
        const mx = moonScreenX();
        const my = moonScreenY();
        const phaseIdx = getMoonPhaseIndex(moonIllum.phaseValue);
        const sprite = MOON_SPRITES[phaseIdx];
        const pixelSize = 3;

        // Subtle pixel glow
        for (let r = 24; r > 0; r -= 5) {
          const a = 0.02 * (1 - r / 24);
          ctx!.fillStyle = `rgba(200, 200, 230, ${a})`;
          ctx!.fillRect(mx - r, my - r, r * 2, r * 2);
        }

        // Draw sprite
        const spriteW = sprite[0].length * pixelSize;
        const spriteH = sprite.length * pixelSize;
        const ox = mx - spriteW / 2;
        const oy = my - spriteH / 2;
        for (let row = 0; row < sprite.length; row++) {
          for (let col = 0; col < sprite[row].length; col++) {
            if (sprite[row][col] === 1) {
              // Lit pixel: slightly off-white for warmth
              const lit = moonIllum.fraction > 0.5
                ? `rgba(240, 235, 245, ${0.8 + Math.sin(time / 2000) * 0.1})`
                : "rgba(230, 225, 240, 0.85)";
              ctx!.fillStyle = lit;
              ctx!.fillRect(
                Math.floor(ox + col * pixelSize),
                Math.floor(oy + row * pixelSize),
                pixelSize,
                pixelSize
              );
            }
          }
        }
      }

      // ── Water reflection (pixel-art) ──
      const waterH = h * 0.18;
      const waterY = h - waterH;
      const pixW = 4;

      // Base water color (reflection of bottom sky band)
      const waterBaseColor = skyColors[5];

      for (const wp of waterPixelsRef.current) {
        const shimmer = Math.sin(time / 1000 * wp.speed + wp.phase);
        const bright = wp.baseBrightness + shimmer * 0.15;
        const clamped = Math.max(0, Math.min(1, bright));

        // Mix sky reflection color with water blue
        const waterBlue = [40, 70, 120];
        const mixed = lerpColor(waterBlue, waterBaseColor, clamped * 0.5);
        const alpha = 0.5 + clamped * 0.3;

        ctx!.fillStyle = rgba(mixed, alpha);
        ctx!.fillRect(wp.x * pixW, waterY + wp.y * pixW, pixW, pixW);
      }

      // Water top edge: pixel-art line
      ctx!.fillStyle = rgba(lerpColor(waterBaseColor, [180, 200, 230], 0.3), 0.6);
      ctx!.fillRect(0, waterY, w, 2);
      // Subtle dashed line for wave effect
      for (let x = 0; x < w; x += 8) {
        const waveY = waterY + 3 + Math.sin(time / 500 + x / 20) * 1.5;
        ctx!.fillStyle = rgba([180, 200, 230], 0.3);
        ctx!.fillRect(x, Math.floor(waveY), 4, 1);
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
