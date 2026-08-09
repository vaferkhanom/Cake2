/**
 * SkyBackground — Pure CSS sky with puffy clouds (day) and diamond stars (night).
 * No external dependencies beyond React. Uses Date() hour for day/night.
 */
import { useMemo, useState, useEffect } from "react";

function generateClouds(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    top: 5 + Math.random() * 75, // 5% to 80% — scattered across the screen
    left: Math.random() * 100,
    scale: 0.6 + Math.random() * 0.8,
    opacity: 0.5 + Math.random() * 0.4,
    duration: 40 + Math.random() * 60,
  }));
}

function generateStars(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    top: Math.random() * 100, // full screen height
    left: Math.random() * 100,
    size: 2 + Math.random() * 5, // 2px to 7px — wider range for small/large contrast
    twinkleDuration: 1.5 + Math.random() * 3,
    twinkleDelay: Math.random() * 4,
    opacity: 0.4 + Math.random() * 0.6,
  }));
}

function getTehranHour(): number {
  const now = new Date();
  const tehranOffset = 3.5 * 60;
  const utcMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
  const tehranMinutes = (utcMinutes + tehranOffset) % (24 * 60);
  return tehranMinutes / 60;
}

function getNightFactor(hour: number): number {
  if (hour >= 6 && hour < 7) return Math.max(0, 1 - (hour - 6));
  if (hour >= 7 && hour < 18) return 0;
  if (hour >= 18 && hour < 20) return Math.min(1, (hour - 18) / 2);
  return 1;
}

export default function SkyBackground() {
  const [nightFactor, setNightFactor] = useState(() => getNightFactor(getTehranHour()));

  useEffect(() => {
    const iv = setInterval(() => setNightFactor(getNightFactor(getTehranHour())), 5 * 60_000);
    return () => clearInterval(iv);
  }, []);

  const isNight = nightFactor > 0.5;
  const isDusk = nightFactor > 0 && nightFactor <= 0.5;
  const clouds = useMemo(() => generateClouds(8), []);
  const stars = useMemo(() => generateStars(50), []);

  const skyStyle = useMemo(() => {
    if (nightFactor > 0.8) {
      return { background: "linear-gradient(180deg, #0B1026 0%, #141B3D 35%, #1A2550 65%, #1E3A5F 100%)" };
    }
    if (isDusk) {
      const t = nightFactor;
      return {
        background: `linear-gradient(180deg,
          rgb(${Math.round(70 + t * -56)}, ${Math.round(130 + t * -110)}, ${Math.round(200 + t * -174)}) 0%,
          rgb(${Math.round(140 + t * -100)}, ${Math.round(180 + t * -120)}, ${Math.round(220 + t * -100)}) 35%,
          rgb(${Math.round(200 + t * -80)}, ${Math.round(200 + t * -100)}, ${Math.round(180 + t * -80)}) 65%,
          rgb(${Math.round(255 - t * 80)}, ${Math.round(180 + t * 30)}, ${Math.round(140 + t * 60)}) 100%)`,
      };
    }
    return { background: "linear-gradient(180deg, #4A9BD9 0%, #7EC8E3 35%, #B5E3F0 65%, #D4EFFA 100%)" };
  }, [nightFactor, isDusk]);

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden transition-colors duration-[3000ms]" style={skyStyle}>
      {/* Clouds — scattered across different parts of the screen */}
      {!isNight && clouds.map((c) => (
        <div key={c.id} className="absolute" style={{
          top: `${c.top}%`, left: `${c.left}%`,
          opacity: c.opacity * (1 - nightFactor * 0.8),
          transform: `scale(${c.scale})`,
          animation: `cloudDrift ${c.duration}s ease-in-out infinite alternate`,
          filter: "blur(1px)", transition: "opacity 3s",
        }}>
          <Cloud />
        </div>
      ))}

      {/* Diamond stars — across the ENTIRE screen */}
      {stars.map((s) => (
        <div
          key={s.id}
          className="absolute"
          style={{
            top: `${s.top}%`, left: `${s.left}%`,
            width: `${s.size}px`, height: `${s.size}px`,
            backgroundColor: `rgba(255, 255, 255, ${s.opacity * nightFactor})`,
            transform: "rotate(45deg)", // diamond shape
            boxShadow: s.size > 3.5
              ? `0 0 ${s.size * 2}px rgba(255, 255, 255, ${0.5 * nightFactor}), 0 0 ${s.size * 4}px rgba(200, 220, 255, ${0.25 * nightFactor})`
              : s.size > 2.5
                ? `0 0 ${s.size * 2}px rgba(255, 255, 255, ${0.35 * nightFactor})`
                : "none",
            animation: nightFactor > 0.3
              ? `starTwinkle ${s.twinkleDuration}s ease-in-out ${s.twinkleDelay}s infinite`
              : "none",
            transition: "opacity 3s, background-color 3s",
          }}
        />
      ))}

      {isDusk && (
        <div className="absolute bottom-0 left-0 right-0" style={{
          height: "30%",
          background: `linear-gradient(180deg, transparent 0%, rgba(255, ${Math.round(150 + (1 - nightFactor) * 50)}, ${Math.round(80 + (1 - nightFactor) * 40)}, ${nightFactor * 0.3}) 100%)`,
        }} />
      )}
    </div>
  );
}

function Cloud() {
  return (
    <div className="relative" style={{ width: "120px", height: "50px" }}>
      <div className="absolute rounded-full" style={{ width: "80px", height: "40px", backgroundColor: "rgba(255,255,255,0.9)", bottom: 0, left: "20px" }} />
      <div className="absolute rounded-full" style={{ width: "50px", height: "40px", backgroundColor: "rgba(255,255,255,0.9)", bottom: "20px", left: "15px" }} />
      <div className="absolute rounded-full" style={{ width: "60px", height: "35px", backgroundColor: "rgba(255,255,255,0.9)", bottom: "18px", left: "45px" }} />
      <div className="absolute rounded-full" style={{ width: "35px", height: "25px", backgroundColor: "rgba(255,255,255,0.85)", bottom: "30px", left: "35px" }} />
    </div>
  );
}
