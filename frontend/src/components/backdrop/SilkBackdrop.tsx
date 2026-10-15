/*
 * Site-wide background: the silk picture, a light wash, and glassy bubbles of
 * different sizes drifting over it.
 *
 * It is a fixed layer at -z-10, so it stays put while the page scrolls. Its
 * parent must create a stacking context (use the `isolate` class), otherwise
 * the layer would fall behind the page background. The layer is decorative:
 * aria-hidden and pointer-events none. Under prefers-reduced-motion everything
 * holds still.
 */

const PICTURE = "/backdrop/silk.jpg";

// Deterministic, so the layout is the same on every visit.
const BUBBLES = [
  { left: "4%", top: "10%", size: 120, dur: 24, delay: 0 },
  { left: "14%", top: "70%", size: 28, dur: 16, delay: 3 },
  { left: "24%", top: "30%", size: 56, dur: 20, delay: 6 },
  { left: "36%", top: "84%", size: 18, dur: 14, delay: 1 },
  { left: "46%", top: "12%", size: 34, dur: 18, delay: 8 },
  { left: "58%", top: "60%", size: 96, dur: 26, delay: 4 },
  { left: "68%", top: "90%", size: 22, dur: 15, delay: 2 },
  { left: "76%", top: "22%", size: 64, dur: 21, delay: 9 },
  { left: "86%", top: "55%", size: 14, dur: 13, delay: 5 },
  { left: "93%", top: "80%", size: 48, dur: 19, delay: 7 },
  { left: "8%", top: "42%", size: 12, dur: 12, delay: 10 },
  { left: "52%", top: "40%", size: 20, dur: 17, delay: 11 },
];

export function SilkBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <style>{`
        @keyframes silkDrift {
          0%, 100% { transform: translate3d(0, 0, 0) scale(1.04); }
          50% { transform: translate3d(-1%, -1.2%, 0) scale(1.07); }
        }
        @keyframes silkRise {
          0% { transform: translate3d(0, 0, 0); }
          50% { transform: translate3d(14px, -34px, 0); }
          100% { transform: translate3d(0, 0, 0); }
        }
        @media (prefers-reduced-motion: reduce) {
          .silk-drift, .silk-bubble { animation: none !important; }
        }
      `}</style>
      <div
        className="silk-drift absolute -inset-[3%]"
        style={{
          backgroundImage: `linear-gradient(rgba(234, 241, 241, 0.25), rgba(234, 241, 241, 0.25)), url(${PICTURE})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          animation: "silkDrift 26s ease-in-out infinite",
        }}
      />
      {BUBBLES.map((b, i) => (
        <span
          key={i}
          className="silk-bubble absolute rounded-full"
          style={{
            left: b.left,
            top: b.top,
            width: b.size,
            height: b.size,
            background:
              "radial-gradient(circle at 30% 28%, rgba(255,255,255,0.95) 0%, rgba(230,242,255,0.55) 35%, rgba(190,215,240,0.25) 70%, rgba(255,255,255,0.12) 100%)",
            border: "1px solid rgba(255,255,255,0.8)",
            boxShadow: "inset -4px -6px 12px rgba(160,190,220,0.25), 0 6px 18px -8px rgba(89,96,112,0.25)",
            animation: `silkRise ${b.dur}s ease-in-out ${b.delay}s infinite`,
          }}
        />
      ))}
    </div>
  );
}
