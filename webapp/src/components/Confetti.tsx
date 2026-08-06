/** Simple SVG confetti burst — 8 particles, 500–600ms, used on DONE. */

export default function Confetti({ active }: { active: boolean }) {
  if (!active) return null;
  const colors = ["#FF8FB1", "#A8D8B9", "#F5B971", "#8EC5F2", "#C9A7E8"];
  const particles = Array.from({ length: 8 }, (_, i) => ({
    x: (i % 4) * 60 - 90,
    y: -((i % 3) + 1) * 40 - 20,
    rotate: (i % 2 ? 1 : -1) * (120 + i * 30),
    color: colors[i % colors.length],
  }));
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {particles.map((p, i) => (
        <div
          key={i}
          className="absolute left-1/2 top-1/2 h-2.5 w-2.5 rounded-full"
          style={{
            background: p.color,
            animation: `confetti 0.55s ease-out ${i * 0.03}s forwards`,
            // @ts-expect-error CSS var for per-particle travel
            "--tx": `${p.x}px`,
            "--ty": `${p.y}px`,
            "--tr": `${p.rotate}deg`,
          }}
        />
      ))}
      <style>{`@keyframes confetti { to { transform: translate(var(--tx), var(--ty)) rotate(var(--tr)); opacity: 0; } }`}</style>
    </div>
  );
}
