/**
 * Live Tehran Sky Background — a living backdrop that follows the real
 * astronomical state of Tehran's sky. Uses SunCalc3 for accurate
 * sun/moon positions and illumination.
 *
 * Renders: sky gradient, sun, moon (with real phase), stars, shooting stars,
 * and a water reflection band at the bottom.
 */

import { useEffect, useMemo, useState } from "react";
import SunCalc from "suncalc3";

// Tehran coordinates
const TEHRAN_LAT = 35.6892;
const TEHRAN_LON = 51.3890;

// Get current time in Tehran timezone
function tehranNow(): Date {
  return new Date(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Tehran" })
  );
}

// Map sun altitude to sky gradient stops
function skyGradient(sunAlt: number): string {
  // Sun well below horizon = deep night
  if (sunAlt < -18) {
    return "linear-gradient(180deg, #0a0e1a 0%, #111833 40%, #1a1040 100%)";
  }
  // Astronomical twilight (-18 to -12)
  if (sunAlt < -12) {
    return "linear-gradient(180deg, #0f1428 0%, #1a2045 40%, #251a40 100%)";
  }
  // Nautical twilight (-12 to -6)
  if (sunAlt < -6) {
    const t = (sunAlt + 18) / 12; // 0 at -18, 1 at -6
    return lerpGradient(
      "linear-gradient(180deg, #1a1830 0%, #2a2050 40%, #3a2040 100%)",
      "linear-gradient(180deg, #2a2055 0%, #5a3060 40%, #cc6644 100%)",
      t
    );
  }
  // Civil twilight / golden hour (-6 to 0)
  if (sunAlt < 0) {
    const t = (sunAlt + 6) / 6;
    return lerpGradient(
      "linear-gradient(180deg, #2a2055 0%, #cc6644 50%, #ffaa55 100%)",
      "linear-gradient(180deg, #5588cc 0%, #88bbee 50%, #ffcc88 100%)",
      t
    );
  }
  // Daytime (0 to 90)
  const t = Math.min(sunAlt / 45, 1); // clamp at noon
  return lerpGradient(
    "linear-gradient(180deg, #5588cc 0%, #88bbee 50%, #ffcc88 100%)",
    "linear-gradient(180deg, #4477bb 0%, #77aadd 50%, #aaddff 100%)",
    t
  );
}

function lerpGradient(a: string, b: string, t: number): string {
  // For simplicity, just crossfade by opacity — both are always visible
  return t < 0.5 ? a : b;
}

// Sun position: map altitude + azimuth to x/y on screen
// In RTL, east is left, west is right
function sunPosition(alt: number, az: number) {
  // altitude: 0 = horizon, 90 = zenith
  // azimuth: 0 = north, PI/2 = east, PI = south, 3PI/2 = west
  const y = Math.max(0, 100 - (alt / 90) * 100); // 0% at top (zenith), 100% at horizon
  // Map azimuth to x: east (PI/2) = left side (20%), west (3PI/2) = right side (80%)
  const azDeg = (az * 180) / Math.PI;
  const x = 20 + ((azDeg - 90) / 180) * 60; // 20% to 80% across screen
  return { x: Math.max(5, Math.min(95, x)), y: Math.max(5, Math.min(95, y)) };
}

// Star positions (generated once, stable)
function generateStars(count: number) {
  const stars = [];
  for (let i = 0; i < count; i++) {
    stars.push({
      x: Math.random() * 100,
      y: Math.random() * 60, // upper 60% of sky only
      size: 1 + Math.random() * 2,
      delay: Math.random() * 5,
      duration: 2 + Math.random() * 4,
    });
  }
  return stars;
}

const STARS = generateStars(80);

export default function LiveSkyBackground() {
  const [now, setNow] = useState(tehranNow);

  // Recompute every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => setNow(tehranNow()), 60_000);
    return () => clearInterval(interval);
  }, []);

  // Sun data
  const sunPos = useMemo(() => SunCalc.getPosition(now, TEHRAN_LAT, TEHRAN_LON), [now]);
  const sunAlt = (sunPos.altitude * 180) / Math.PI; // degrees
  const sunAz = sunPos.azimuth + Math.PI; // normalize: 0=north, clockwise

  // Moon data
  const moonPos = useMemo(() => SunCalc.getMoonPosition(now, TEHRAN_LAT, TEHRAN_LON), [now]);
  const moonIllum = useMemo(() => SunCalc.getMoonIllumination(now), [now]);
  const moonAlt = (moonPos.altitude * 180) / Math.PI;
  const moonAz = moonPos.azimuth + Math.PI;

  // Is it night? (sun below civil twilight)
  const isNight = sunAlt < -6;
  const isDusk = sunAlt >= -6 && sunAlt < 0;

  // Background gradient
  const gradient = skyGradient(sunAlt);

  // Sun position on screen
  const sun = sunPosition(sunAlt, sunAz);
  const showSun = sunAlt > -2; // show sun when near/above horizon

  // Moon position on screen
  const moon = moonPosition(moonAlt, moonAz);
  const showMoon = moonAlt > -5 && moonIllum.fraction > 0.02;

  // Star visibility: fade in during dusk, fully visible at night
  const starOpacity = isNight ? 1 : isDusk ? Math.min(1, (-sunAlt - 0) / 6) : 0;

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      {/* Sky gradient layer */}
      <div className="absolute inset-0 transition-all duration-[3000ms]" style={{ background: gradient }} />

      {/* Stars */}
      {starOpacity > 0 && (
        <div className="absolute inset-0" style={{ opacity: starOpacity }}>
          {STARS.map((star, i) => (
            <div
              key={i}
              className="absolute rounded-full bg-white"
              style={{
                left: `${star.x}%`,
                top: `${star.y}%`,
                width: star.size,
                height: star.size,
                animation: `twinkle ${star.duration}s ease-in-out ${star.delay}s infinite`,
              }}
            />
          ))}
        </div>
      )}

      {/* Sun */}
      {showSun && (
        <div
          className="absolute rounded-full"
          style={{
            left: `${sun.x}%`,
            top: `${sun.y}%`,
            width: 48,
            height: 48,
            transform: "translate(-50%, -50%)",
            background: sunAlt > 0
              ? "radial-gradient(circle, #fff8e1 0%, #ffd54f 40%, #ff8f00 80%, transparent 100%)"
              : "radial-gradient(circle, #ff6644 0%, #cc4422 50%, transparent 100%)",
            boxShadow: sunAlt > 0
              ? "0 0 60px 20px rgba(255,213,79,0.4), 0 0 120px 40px rgba(255,183,77,0.2)"
              : "0 0 40px 15px rgba(204,68,34,0.3)",
            opacity: sunAlt > 0 ? 1 : Math.max(0, (sunAlt + 2) / 2),
          }}
        />
      )}

      {/* Moon */}
      {showMoon && (
        <div
          className="absolute"
          style={{
            left: `${moon.x}%`,
            top: `${moon.y}%`,
            width: 36,
            height: 36,
            transform: "translate(-50%, -50%)",
          }}
        >
          <MoonPhase
            fraction={moonIllum.fraction}
            phase={moonIllum.phase}
          />
        </div>
      )}

      {/* Water reflection */}
      <div
        className="absolute bottom-0 left-0 right-0 h-[18%]"
        style={{
          background: gradient,
          transform: "scaleY(-1)",
          opacity: 0.35,
          filter: "blur(2px)",
          maskImage: "linear-gradient(to bottom, rgba(0,0,0,0.5), transparent)",
          WebkitMaskImage: "linear-gradient(to bottom, rgba(0,0,0,0.5), transparent)",
        }}
      />

      {/* Shooting star (random interval) */}
      <ShootingStar />

      {/* Twinkle keyframes */}
      <style>{`
        @keyframes twinkle {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// Moon position (same logic as sun but for moon)
function moonPosition(alt: number, az: number) {
  const y = Math.max(0, 100 - (alt / 90) * 100);
  const azDeg = (az * 180) / Math.PI;
  const x = 20 + ((azDeg - 90) / 180) * 60;
  return { x: Math.max(5, Math.min(95, x)), y: Math.max(5, Math.min(95, y)) };
}

// Moon phase SVG rendering
function MoonPhase({ fraction, phase }: { fraction: number; phase: number }) {
  // phase: 0=new, 0.25=first quarter, 0.5=full, 0.75=last quarter, 1=new
  // fraction: how much is illuminated (0 to 1)
  const r = 16;
  const cx = 18;
  const cy = 18;

  // The terminator is an ellipse. Its x-radius depends on the phase.
  // At full moon (phase=0.5), terminator is at edge → full circle visible
  // At new moon (phase=0), terminator covers everything
  // At quarter (phase=0.25 or 0.75), terminator is a straight line

  const terminatorX = r * Math.abs(Math.cos(phase * 2 * Math.PI));
  const isWaxing = phase < 0.5;

  // Build SVG path for the lit portion
  // We use two arcs: one for the outer edge (always a semicircle),
  // one for the terminator (ellipse)
  const sweep1 = isWaxing ? 1 : 0;
  const sweep2 = isWaxing ? 0 : 1;

  const path = `
    M ${cx} ${cy - r}
    A ${r} ${r} 0 0 ${sweep1} ${cx} ${cy + r}
    A ${terminatorX} ${r} 0 0 ${sweep2} ${cx} ${cy - r}
    Z
  `;

  return (
    <svg width="36" height="36" viewBox="0 0 36 36">
      {/* Dark base */}
      <circle cx={cx} cy={cy} r={r} fill="rgba(200,200,220,0.15)" />
      {/* Lit portion */}
      {fraction > 0.01 && (
        <path d={path} fill="rgba(240,235,245,0.9)" />
      )}
      {/* Subtle glow */}
      <circle
        cx={cx}
        cy={cy}
        r={r + 4}
        fill="none"
        stroke="rgba(200,200,220,0.08)"
        strokeWidth="3"
      />
    </svg>
  );
}

// Shooting star component
function ShootingStar() {
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0, angle: 0 });

  useEffect(() => {
    const schedule = () => {
      const delay = 60_000 + Math.random() * 180_000; // 1-4 minutes
      return setTimeout(() => {
        setPos({
          x: 20 + Math.random() * 60,
          y: 5 + Math.random() * 30,
          angle: 20 + Math.random() * 40,
        });
        setVisible(true);
        setTimeout(() => setVisible(false), 1200);
        timerRef = schedule();
      }, delay);
    };
    let timerRef = schedule();
    return () => clearTimeout(timerRef);
  }, []);

  if (!visible) return null;

  return (
    <div
      className="absolute"
      style={{
        left: `${pos.x}%`,
        top: `${pos.y}%`,
        width: 80,
        height: 2,
        background: "linear-gradient(90deg, rgba(255,255,255,0.9), transparent)",
        borderRadius: 2,
        transform: `rotate(${pos.angle}deg)`,
        animation: "shootingStar 1.2s ease-out forwards",
      }}
    >
      <style>{`
        @keyframes shootingStar {
          0% { opacity: 1; transform: translateX(0) rotate(${pos.angle}deg); }
          100% { opacity: 0; transform: translateX(200px) rotate(${pos.angle}deg); }
        }
      `}</style>
    </div>
  );
}
