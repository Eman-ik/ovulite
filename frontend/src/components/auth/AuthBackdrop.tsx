/*
 * Moving background for the login and signup pages.
 *
 * The sphere picture drifts slowly, and a few glints rise through it, so the
 * bubbles look alive. The picture is oversized so its edges never show while it
 * moves. Everything here is decorative: aria-hidden and pointer-events none.
 * Under prefers-reduced-motion it stays still.
 */

const BACKGROUND = "/auth/login-bg.png";

const GLINTS = [
  { left: "12%", size: 16, dur: 16, delay: 0 },
  { left: "28%", size: 10, dur: 21, delay: 4 },
  { left: "46%", size: 22, dur: 18, delay: 2 },
  { left: "63%", size: 12, dur: 24, delay: 7 },
  { left: "78%", size: 18, dur: 19, delay: 1 },
  { left: "90%", size: 9, dur: 15, delay: 5 },
];

export function AuthBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <style>{`
        @keyframes authDrift {
          0%, 100% { transform: translate3d(0, 0, 0) scale(1.06); }
          50% { transform: translate3d(-1.2%, -1.6%, 0) scale(1.09); }
        }
        @keyframes authRise {
          0% { transform: translateY(0); opacity: 0; }
          15% { opacity: 0.85; }
          85% { opacity: 0.85; }
          100% { transform: translateY(-110vh); opacity: 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .auth-drift, .auth-glint { animation: none !important; }
        }
      `}</style>
      <div
        className="auth-drift absolute -inset-[4%]"
        style={{
          backgroundImage: `url(${BACKGROUND})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          animation: "authDrift 22s ease-in-out infinite",
        }}
      />
      {GLINTS.map((g, i) => (
        <span
          key={i}
          className="auth-glint absolute bottom-[-8%] rounded-full"
          style={{
            left: g.left,
            width: g.size,
            height: g.size,
            background:
              "radial-gradient(circle at 32% 28%, rgba(255,255,255,0.95) 0%, rgba(214,236,255,0.5) 45%, rgba(255,255,255,0.05) 100%)",
            border: "1px solid rgba(255,255,255,0.8)",
            animation: `authRise ${g.dur}s linear ${g.delay}s infinite`,
          }}
        />
      ))}
    </div>
  );
}
