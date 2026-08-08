/**
 * SkyBackground — Simple CSS-based sky with puffy clouds (day) and stars (night).
 * No canvas, no heavy animation loop — lightweight and performant.
 * Uses SunCalc (via dynamic import) for Tehran day/night detection.
 */

import { useEffect, useMemo, useState } from "react";

const TEHRAN_LAT = 35.6892;
const TEHRAN_LON = 51.3890;

// Generate random cloud positions (stable across re-renders)
function generateClouds(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    top: 5 + Math.random() * 45,
    left: Math.random() * 100,
    scale: 0.6 + Math.random() * 0.8,
    opacity: 0.5 + Math.random() * 0.4,
    duration: 40 + Math.random() * 60,
  }));
}

// Generate random star positions
function generateStars(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    top: Math.random() * 55,
    left: Math.random() * 100,
    size: 1 + Math.random() * 3,
    twinkleDuration: 1.5 + Math.random() * 3,
    twinkleDelay: Math.random() * 4,
    opacity: 0.4 + Math.random() * 0.6,
  }));
}

export default function SkyBackground() {
  const [sunAlt, setSunAlt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const compute = async () => {
      try {
        const SunCalc = await import("suncalc");
        if (cancelled) return;
        const sp = SunCalc.getPosition(new Date(), TEHRAN_LAT, TEHRAN_LON);
        setSunAlt((sp.altitude * 180) / Math.PI);
      } catch (err) {
        console.error("[SkyBackground] suncalc import failed:", err);
        // Default to daytime if suncalc fails
        if (!cancelled) setSunAlt(30);
      }
    };
    compute();
    const iv = setInterval(compute, 5 * 60_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  const isNight = sunAlt < -6;
  const isDusk = sunAlt >= -6 && sunAlt < 0;
  const nightFactor = Math.max(0, Math.min(1, (-sunAlt) / 18));

  const clouds = useMemo(() => generateClouds(8), []);
  const stars = useMemo(() => generateStars(50), []);

  const skyStyle = useMemo(() => {
    if (isNight) {
      return {
        background: "linear-gradient(180deg, #0B1026 0%, #141B3D 35%, #1A2550 65%, #1E3A5F 100%)",
      };
    }
    if (isDusk) {
      const t = Math.min(1, (-sunAlt) / 6);
      return {
        background: `linear-gradient(180deg, 
          rgb(${Math.round(70 + t * -56)}, ${Math.round(130 + t * -110)}, ${Math.round(200 + t * -174)}) 0%, 
          rgb(${Math.round(140 + t * -100)}, ${Math.round(180 + t * -120)}, ${Math.round(220 + t * -100)}) 35%, 
          rgb(${Math.round(200 + t * -80)}, ${Math.round(200 + t * -100)}, ${Math.round(180 + t * -80)}) 65%, 
          rgb(${Math.round(255 - t * 80)}, ${Math.round(180 + t * 30)}, ${Math.round(140 + t * 60)}) 100%)`,
      };
    }
    return {
      background: "linear-gradient(180deg, #4A9BD9 0%, #7EC8E3 35%, #B5E3F0 65%, #D4EFFA 100%)",
    };
  }, [isNight, isDusk, sunAlt]);

  return (
    <div
      className="fixed inset-0 -z-10 overflow-hidden transition-colors duration-[3000ms]"
      style={skyStyle}
    >
      {!isNight && clouds.map((c) => (
        <div
          key={c.id}
          className="absolute"
          style={{
            top: `${c.top}%`,
            left: `${c.left}%`,
            opacity: c.opacity * (1 - nightFactor * 0.8),
            transform: `scale(${c.scale})`,
            animation: `cloudDrift ${c.duration}s ease-in-out infinite alternate`,
            filter: "blur(1px)",
            transition: "opacity 3s",
          }}
        >
          <Cloud />
        </div>
      ))}

      {stars.map((s) => (
        <div
          key={s.id}
          className="absolute rounded-full"
          style={{
            top: `${s.top}%`,
            left: `${s.left}%`,
            width: `${s.size}px`,
            height: `${s.size}px`,
            backgroundColor: `rgba(255, 255, 255, ${s.opacity * nightFactor})`,
            boxShadow: s.size > 2.5
              ? `0 0 ${s.size * 2}px rgba(255, 255, 255, ${0.4 * nightFactor})`
              : "none",
            animation: nightFactor > 0.3
              ? `starTwinkle ${s.twinkleDuration}s ease-in-out ${s.twinkleDelay}s infinite`
              : "none",
            transition: "opacity 3s, background-color 3s",
          }}
        />
      ))}

      {isDusk && (
        <div
          className="absolute bottom-0 left-0 right-0"
          style={{
            height: "30%",
            background: `linear-gradient(180deg, transparent 0%, rgba(255, ${Math.round(150 + (1 - nightFactor) * 50)}, ${Math.round(80 + (1 - nightFactor) * 40)}, ${nightFactor * 0.3}) 100%)`,
          }}
        />
      )}
    </div>
  );
}

function Cloud() {
  return (
    <div className="relative" style={{ width: "120px", height: "50px" }}>
      <div
        className="absolute rounded-full"
        style={{ width: "80px", height: "40px", backgroundColor: "rgba(255, 255, 255, 0.9)", bottom: 0, left: "20px" }}
      />
      <div
        className="absolute rounded-full"
        style={{ width: "50px", height: "40px", backgroundColor: "rgba(255, 255, 255, 0.9)", bottom: "20px", left: "15px" }}
      />
      <div
        className="absolute rounded-full"
        style={{ width: "60px", height: "35px", backgroundColor: "rgba(255, 255, 255, 0.9)", bottom: "18px", left: "45px" }}
      />
      <div
        className="absolute rounded-full"
        style={{ width: "35px", height: "25px", backgroundColor: "rgba(255, 255, 255, 0.85)", bottom: "30px", left: "35px" }}
      />
    </div>
  );
}
