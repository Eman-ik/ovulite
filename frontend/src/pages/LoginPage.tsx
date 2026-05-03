import ovuliteLogo from "./icon.png";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  ArrowRight,
  Eye,
  EyeOff,
  Lock,
  Mail,
  Moon,
  Sun,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

/* ─────────────────────────────────────────────
   Animation styles injected once into <head>
───────────────────────────────────────────── */
const PAGE_STYLES = `
  /* ── Night / smog ── */
  @keyframes fogDrift1 {
    0%,100% { transform: translateX(0%)  scaleY(1);    opacity: 0.55; }
    50%     { transform: translateX(6%)  scaleY(1.08); opacity: 0.70; }
  }
  @keyframes fogDrift2 {
    0%,100% { transform: translateX(0%)  scaleY(1);    opacity: 0.40; }
    50%     { transform: translateX(-5%) scaleY(1.12); opacity: 0.60; }
  }
  @keyframes fogDrift3 {
    0%,100% { transform: translateX(0%) scaleY(1);    opacity: 0.30; }
    60%     { transform: translateX(4%) scaleY(1.06); opacity: 0.50; }
  }
  @keyframes starTwinkle {
    0%,100% { opacity: 0.5; }
    50%     { opacity: 1.0; }
  }
  @keyframes dustFloat {
    0%   { transform: translateY(0px)   translateX(0px);  opacity: 0.18; }
    33%  { transform: translateY(-12px) translateX(6px);  opacity: 0.32; }
    66%  { transform: translateY(-6px)  translateX(-4px); opacity: 0.22; }
    100% { transform: translateY(0px)   translateX(0px);  opacity: 0.18; }
  }
  @keyframes smokeRise {
    0%,100% { transform: translateY(0)    scaleX(1);   opacity: 0.18; }
    50%     { transform: translateY(-30px) scaleX(1.1); opacity: 0.28; }
  }
  /* sweeping spotlight beam */
  @keyframes spotlightSweep {
    0%,100% { transform: rotate(-18deg) scaleX(1);   opacity: 0.92; }
    40%     { transform: rotate(-10deg) scaleX(1.04); opacity: 1;    }
    70%     { transform: rotate(-22deg) scaleX(0.97); opacity: 0.88; }
  }
  /* subtle spotlight flicker */
  @keyframes spotlightFlicker {
    0%,100% { opacity: 1;    }
    20%     { opacity: 0.94; }
    45%     { opacity: 0.98; }
    72%     { opacity: 0.90; }
  }

  .fog-layer-1    { animation: fogDrift1       18s ease-in-out infinite; }
  .fog-layer-2    { animation: fogDrift2       24s ease-in-out infinite; }
  .fog-layer-3    { animation: fogDrift3       30s ease-in-out infinite; }
  .smoke-rise     { animation: smokeRise       20s ease-in-out infinite; }
  .spotlight-beam { animation: spotlightSweep  12s ease-in-out infinite,
                               spotlightFlicker 3s  ease-in-out infinite; }

  /* ── Light / bubbles ── */
  @keyframes bubbleFloat {
    0%   { transform: translateY(0px)    rotate(0deg);   }
    25%  { transform: translateY(-18px)  rotate(3deg);   }
    50%  { transform: translateY(-8px)   rotate(-2deg);  }
    75%  { transform: translateY(-22px)  rotate(2deg);   }
    100% { transform: translateY(0px)    rotate(0deg);   }
  }
  @keyframes bubbleShimmer {
    0%,100% { opacity: 0.55; }
    50%     { opacity: 0.80; }
  }
  .bubble { animation: bubbleFloat   var(--dur,10s) ease-in-out infinite var(--delay,0s),
                       bubbleShimmer var(--sdur,6s) ease-in-out infinite var(--sdelay,0s); }
`;

/* ══════════════════════════════════════════════
   DARK — Night atmosphere with spotlight
══════════════════════════════════════════════ */
function NightAtmosphere() {
  return (
    <>
      {/* Deep night sky */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at 30% 0%, #1a0f2e 0%, #0a0a14 40%, #050508 100%)",
          zIndex: 0,
        }}
      />

      {/* ── SPOTLIGHT from top-right ── */}
      {/* outer soft cone */}
      <div
        className="spotlight-beam pointer-events-none absolute"
        style={{
          top: "-6%",
          right: "10%",
          width: 420,
          height: "110vh",
          transformOrigin: "50% 0%",
          background:
            "conic-gradient(from -6deg at 50% 0%, transparent 0deg, rgba(255,200,100,0.06) 8deg, rgba(255,180,60,0.13) 14deg, rgba(255,200,100,0.06) 20deg, transparent 28deg)",
          filter: "blur(6px)",
          zIndex: 2,
        }}
      />
      {/* inner bright core beam */}
      <div
        className="spotlight-beam pointer-events-none absolute"
        style={{
          top: "-4%",
          right: "16%",
          width: 180,
          height: "100vh",
          transformOrigin: "50% 0%",
          background:
            "linear-gradient(to bottom, rgba(255,220,140,0.28) 0%, rgba(255,180,60,0.10) 35%, rgba(255,140,40,0.03) 70%, transparent 100%)",
          clipPath: "polygon(30% 0%, 70% 0%, 100% 100%, 0% 100%)",
          filter: "blur(3px)",
          zIndex: 3,
          animationDelay: "0.3s",
        }}
      />
      {/* dust motes caught in the beam */}
      {[
        { right: "22%", top: "18%", size: 2.5, delay: "0s",   dur: "7s"  },
        { right: "19%", top: "34%", size: 1.5, delay: "1.2s", dur: "9s"  },
        { right: "24%", top: "52%", size: 2.0, delay: "2.5s", dur: "6s"  },
        { right: "18%", top: "25%", size: 1.2, delay: "0.8s", dur: "11s" },
        { right: "21%", top: "44%", size: 1.8, delay: "3.1s", dur: "8s"  },
      ].map((p, i) => (
        <div
          key={`beam-mote-${i}`}
          className="pointer-events-none absolute rounded-full"
          style={{
            right: p.right,
            top: p.top,
            width: p.size * 2,
            height: p.size * 2,
            background: "rgba(255,220,160,0.7)",
            filter: "blur(1px)",
            animation: `dustFloat ${p.dur} ease-in-out infinite`,
            animationDelay: p.delay,
            zIndex: 4,
          }}
        />
      ))}
      {/* spotlight source — small bright point, no ball shape */}
      <div
        className="pointer-events-none absolute"
        style={{
          top: 0,
          right: "17%",
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,240,200,0.95) 0%, rgba(255,210,100,0.5) 50%, transparent 100%)",
          filter: "blur(4px)",
          zIndex: 5,
        }}
      />

      {/* Stars */}
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        style={{ zIndex: 1 }}
        xmlns="http://www.w3.org/2000/svg"
      >
        {[
          [8,4,1.2,2.1],[18,9,0.8,3.4],[34,3,1.5,1.8],[52,7,1.0,4.2],
          [67,2,0.7,2.8],[80,11,1.3,1.5],[91,5,0.9,3.9],[12,18,1.1,2.5],
          [27,14,1.4,1.2],[43,20,0.6,4.6],[58,16,1.2,3.1],[74,8,0.8,2.3],
          [88,19,1.0,1.7],[5,28,0.7,4.8],[22,32,1.3,2.0],[39,25,0.9,3.5],
          [55,30,1.5,1.4],[71,22,0.6,4.1],[85,27,1.1,2.7],[96,15,0.8,3.3],
        ].map(([cx,cy,r,delay],i) => (
          <circle
            key={i} cx={`${cx}%`} cy={`${cy}%`} r={r} fill="white"
            style={{
              animation: `starTwinkle ${2.5+delay*0.4}s ease-in-out infinite`,
              animationDelay: `${delay}s`, opacity: 0.7,
            }}
          />
        ))}
      </svg>

      {/* City glow horizon */}
      <div className="pointer-events-none absolute bottom-0 left-0 right-0" style={{
        height:"38%",
        background:"radial-gradient(ellipse at 50% 100%, rgba(255,90,20,0.22) 0%, rgba(200,60,10,0.1) 40%, transparent 70%)",
        zIndex:1,
      }}/>
      <div className="pointer-events-none absolute bottom-0" style={{
        left:"15%",width:"40%",height:"30%",
        background:"radial-gradient(ellipse at 50% 100%, rgba(255,120,30,0.14) 0%, transparent 70%)",
        zIndex:1,
      }}/>

      {/* Smog layers */}
      <div className="fog-layer-1 pointer-events-none absolute bottom-0 left-0 right-0" style={{
        height:"28%",
        background:"linear-gradient(to top, rgba(60,30,10,0.65) 0%, rgba(80,40,15,0.35) 40%, transparent 100%)",
        filter:"blur(18px)", zIndex:2,
      }}/>
      <div className="fog-layer-2 pointer-events-none absolute" style={{
        bottom:"20%",left:"-10%",width:"70%",height:"22%",
        background:"radial-gradient(ellipse at 40% 60%, rgba(120,80,40,0.28) 0%, rgba(80,50,20,0.12) 60%, transparent 100%)",
        filter:"blur(28px)", zIndex:2,
      }}/>
      <div className="fog-layer-3 pointer-events-none absolute" style={{
        top:"28%",right:"-5%",width:"55%",height:"18%",
        background:"radial-gradient(ellipse at 60% 40%, rgba(60,60,80,0.22) 0%, rgba(40,40,60,0.08) 60%, transparent 100%)",
        filter:"blur(32px)", zIndex:2,
      }}/>

      {/* Smoke wisps */}
      <div className="smoke-rise pointer-events-none absolute" style={{
        bottom:"10%",left:"8%",width:180,height:260,
        background:"radial-gradient(ellipse at 50% 80%, rgba(100,70,40,0.22) 0%, transparent 70%)",
        filter:"blur(22px)", zIndex:2,
      }}/>
      <div className="smoke-rise pointer-events-none absolute" style={{
        bottom:"8%",right:"18%",width:140,height:200,
        background:"radial-gradient(ellipse at 50% 80%, rgba(80,60,30,0.18) 0%, transparent 70%)",
        filter:"blur(20px)", zIndex:2, animationDelay:"7s",
      }}/>

      {/* Ambient dust particles */}
      {[
        {left:"12%",top:"55%",size:3,  delay:"0s",  dur:"8s" },
        {left:"28%",top:"40%",size:2,  delay:"2s",  dur:"11s"},
        {left:"45%",top:"65%",size:2.5,delay:"4s",  dur:"9s" },
        {left:"62%",top:"48%",size:1.5,delay:"1s",  dur:"13s"},
        {left:"78%",top:"58%",size:2,  delay:"5s",  dur:"10s"},
        {left:"20%",top:"72%",size:1.5,delay:"6s",  dur:"7s" },
        {left:"55%",top:"33%",size:2,  delay:"2.5s",dur:"14s"},
      ].map((p,i)=>(
        <div key={`dust-${i}`} className="pointer-events-none absolute rounded-full" style={{
          left:p.left,top:p.top,width:p.size*2,height:p.size*2,
          background:"rgba(255,160,60,0.55)",filter:"blur(1px)",
          animation:`dustFloat ${p.dur} ease-in-out infinite`,
          animationDelay:p.delay, zIndex:3,
        }}/>
      ))}

      {/* Noise grain */}
      <div className="pointer-events-none absolute inset-0" style={{
        zIndex:4, opacity:0.045,
        backgroundImage:`url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
        backgroundRepeat:"repeat", backgroundSize:"200px 200px",
      }}/>

      {/* Vignette */}
      <div className="pointer-events-none absolute inset-0" style={{
        background:"radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(0,0,0,0.55) 100%)",
        zIndex:4,
      }}/>
    </>
  );
}

/* ══════════════════════════════════════════════
   LIGHT — Floating glass bubbles
══════════════════════════════════════════════ */
const BUBBLES = [
  { size: 90,  left: "6%",  top: "12%", dur: "11s", delay: "0s",   sdur: "7s",  sdelay: "0s"   },
  { size: 54,  left: "82%", top: "8%",  dur: "14s", delay: "2s",   sdur: "9s",  sdelay: "1s"   },
  { size: 120, left: "88%", top: "42%", dur: "9s",  delay: "0.5s", sdur: "6s",  sdelay: "3s"   },
  { size: 40,  left: "3%",  top: "55%", dur: "13s", delay: "3s",   sdur: "8s",  sdelay: "1.5s" },
  { size: 70,  left: "14%", top: "76%", dur: "10s", delay: "1.5s", sdur: "11s", sdelay: "0.5s" },
  { size: 48,  left: "72%", top: "70%", dur: "16s", delay: "4s",   sdur: "7s",  sdelay: "2s"   },
  { size: 30,  left: "55%", top: "5%",  dur: "12s", delay: "1s",   sdur: "9s",  sdelay: "4s"   },
  { size: 80,  left: "40%", top: "82%", dur: "8s",  delay: "2.5s", sdur: "6s",  sdelay: "0s"   },
  { size: 35,  left: "92%", top: "22%", dur: "15s", delay: "0s",   sdur: "10s", sdelay: "2.5s" },
  { size: 60,  left: "25%", top: "18%", dur: "11s", delay: "3.5s", sdur: "8s",  sdelay: "1s"   },
];

function GlassBubbles() {
  return (
    <>
      {BUBBLES.map((b, i) => (
        <div
          key={i}
          className="bubble pointer-events-none absolute"
          style={{
            left: b.left,
            top: b.top,
            width: b.size,
            height: b.size,
            borderRadius: "50%",
            /* glass effect: layered radial + linear gradients */
            background: [
              "radial-gradient(circle at 35% 30%, rgba(255,255,255,0.72) 0%, rgba(255,255,255,0.08) 55%, transparent 100%)",
              "radial-gradient(circle at 70% 75%, rgba(180,220,255,0.30) 0%, transparent 60%)",
              "linear-gradient(135deg, rgba(255,255,255,0.55) 0%, rgba(160,200,255,0.15) 50%, rgba(120,180,255,0.08) 100%)",
            ].join(", "),
            border: "1px solid rgba(255,255,255,0.68)",
            boxShadow: [
              "inset 0 1px 2px rgba(255,255,255,0.9)",
              "inset -2px -2px 6px rgba(120,180,255,0.18)",
              "0 8px 32px rgba(100,160,255,0.10)",
              "0 2px 8px rgba(255,255,255,0.40)",
            ].join(", "),
            backdropFilter: "blur(6px)",
            zIndex: 1,
            "--dur":   b.dur,
            "--delay": b.delay,
            "--sdur":  b.sdur,
            "--sdelay":b.sdelay,
          } as React.CSSProperties}
        >
          {/* specular highlight — tiny bright crescent top-left */}
          <div style={{
            position:"absolute", top:"14%", left:"18%",
            width:"30%", height:"14%",
            borderRadius:"50%",
            background:"rgba(255,255,255,0.85)",
            filter:"blur(2px)",
            transform:"rotate(-30deg)",
          }}/>
          {/* secondary soft reflection bottom-right */}
          <div style={{
            position:"absolute", bottom:"18%", right:"14%",
            width:"22%", height:"10%",
            borderRadius:"50%",
            background:"rgba(180,220,255,0.55)",
            filter:"blur(3px)",
            transform:"rotate(20deg)",
          }}/>
        </div>
      ))}
    </>
  );
}

/* ══════════════════════════════════════════════
   MAIN PAGE
══════════════════════════════════════════════ */
export default function LoginPage() {
  const { login, user, isLoading: authLoading } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === "undefined") return false;
    return (
      localStorage.getItem("ovulite_theme") === "dark" ||
      document.documentElement.classList.contains("dark")
    );
  });

  useEffect(() => {
    const id = "ovulite-page-styles";
    if (!document.getElementById(id)) {
      const tag = document.createElement("style");
      tag.id = id;
      tag.textContent = PAGE_STYLES;
      document.head.appendChild(tag);
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) root.classList.add("dark");
    else root.classList.remove("dark");
    localStorage.setItem("ovulite_theme", isDark ? "dark" : "light");
  }, [isDark]);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="flex items-center gap-3 rounded-2xl border border-white/30 bg-white/60 px-6 py-4 shadow-lg backdrop-blur-xl">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <span className="text-sm text-slate-600">Authenticating secure session...</span>
        </div>
      </div>
    );
  }

  if (user) return <Navigate to="/app" replace />;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response
                ?.data?.detail || "Login failed. Please check your credentials."
            : "Login failed. Please check your credentials.";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const inputBase =
    "w-full rounded-full py-4 pl-12 pr-4 text-sm shadow-sm outline-none transition-all";
  const inputStyle = {
    background: isDark ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.65)",
    border: isDark ? "1px solid rgba(255,255,255,0.09)" : "1px solid rgba(255,255,255,0.85)",
    color: isDark ? "#f4f4f5" : "#1e293b",
  };
  const onFocusInput = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.boxShadow = isDark
      ? "0 0 0 4px rgba(255,107,0,0.22)"
      : "0 0 0 4px rgba(59,130,246,0.2)";
    e.currentTarget.style.borderColor = isDark ? "rgba(255,107,0,0.55)" : "rgba(59,130,246,0.4)";
    e.currentTarget.style.background  = isDark ? "rgba(255,255,255,0.09)" : "#ffffff";
  };
  const onBlurInput = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.boxShadow   = "none";
    e.currentTarget.style.borderColor = isDark ? "rgba(255,255,255,0.09)" : "rgba(255,255,255,0.85)";
    e.currentTarget.style.background  = isDark ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.65)";
  };

  return (
    <div
      className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-8 sm:px-6"
      style={{
        background: isDark
          ? "#060608"
          : "radial-gradient(circle at top left, #cfe8ff 0%, #f0f6ff 50%, #ddeeff 100%)",
        transition: "background 0.5s ease",
      }}
    >
      {/* ── LIGHT: blue orbs + glass bubbles ── */}
      {!isDark && (
        <>
          <div className="pointer-events-none absolute -left-20 -top-20 h-[28rem] w-[28rem] rounded-full bg-blue-300/40 blur-[110px]" style={{zIndex:0}}/>
          <div className="pointer-events-none absolute bottom-8 right-8 h-[22rem] w-[22rem] rounded-full bg-blue-200/30 blur-[90px]" style={{zIndex:0}}/>
          <GlassBubbles />
        </>
      )}

      {/* ── DARK: full night atmosphere with spotlight ── */}
      {isDark && <NightAtmosphere />}

      {/* ── TOGGLE ── */}
      <button
        type="button"
        aria-label="Toggle dark mode"
        onClick={() => setIsDark(v => !v)}
        className="fixed right-5 top-5 z-50 flex h-10 w-10 items-center justify-center rounded-full shadow-md backdrop-blur-md transition-all hover:scale-110 active:scale-95"
        style={{
          background: isDark ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.8)",
          border: isDark ? "1px solid rgba(255,255,255,0.12)" : "1px solid rgba(255,255,255,0.75)",
        }}
      >
        {isDark
          ? <Sun  className="h-4 w-4 text-orange-400" />
          : <Moon className="h-4 w-4 text-blue-500"   />}
      </button>

      {/* ── CARD ── */}
      <div className="relative z-10 w-full max-w-[1200px]">
        <div
          className="mx-auto w-full max-w-[520px] rounded-[2rem] p-8 md:p-12 backdrop-blur-3xl transition-all duration-500"
          style={{
            background: isDark ? "rgba(14,12,18,0.82)" : "rgba(255,255,255,0.72)",
            border: isDark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(255,255,255,0.88)",
            boxShadow: isDark
              ? "0 8px 64px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.06)"
              : "0 8px 48px rgba(100,160,255,0.13)",
          }}
        >
          {/* HEADER */}
          <div className="mb-10 flex flex-col items-center gap-4 text-center">
            <div
              className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border-2 shadow-xl"
              style={{
                borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.9)",
                background: isDark ? "rgba(0,0,0,0.5)" : "#ffffff",
                boxShadow: isDark ? "0 0 24px rgba(255,140,0,0.2)" : undefined,
              }}
            >
              <img src={ovuliteLogo} alt="Ovulite logo" className="h-full w-full object-cover" />
            </div>

            <div
              className="rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-[0.16em]"
              style={{
                background: isDark ? "rgba(255,107,0,0.12)" : "rgba(255,255,255,0.8)",
                border: isDark ? "1px solid rgba(255,107,0,0.3)" : "1px solid rgba(255,255,255,0.8)",
                color: isDark ? "#fb923c" : "#475569",
              }}
            >
              Secure Access
            </div>

            <div>
              <h1 className="mb-2 text-3xl font-extrabold tracking-tight"
                style={{ color: isDark ? "#f4f4f5" : "#0f172a" }}>
                Welcome to Ovulite
              </h1>
              <p className="text-sm font-medium"
                style={{ color: isDark ? "#71717a" : "#64748b" }}>
                Access your reproductive intelligence dashboard.
              </p>
            </div>
          </div>

          {/* FORM */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email */}
            <label className="block">
              <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider"
                style={{ color: isDark ? "#d4d4d8" : "#1e293b" }}>
                Email Address
              </span>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2"
                  style={{ color: isDark ? "#52525b" : "#94a3b8" }} />
                <input type="text" required placeholder="name@company.com"
                  value={username} onChange={e => setUsername(e.target.value)}
                  onFocus={onFocusInput} onBlur={onBlurInput}
                  className={inputBase} style={inputStyle} />
              </div>
            </label>

            {/* Password */}
            <label className="block">
              <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider"
                style={{ color: isDark ? "#d4d4d8" : "#1e293b" }}>
                Password
              </span>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2"
                  style={{ color: isDark ? "#52525b" : "#94a3b8" }} />
                <input type={showPassword ? "text" : "password"} required placeholder="••••••••"
                  value={password} onChange={e => setPassword(e.target.value)}
                  onFocus={onFocusInput} onBlur={onBlurInput}
                  className={`${inputBase} pr-12`} style={inputStyle} />
                <button type="button" onClick={() => setShowPassword(v => !v)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: isDark ? "#52525b" : "#94a3b8" }}
                  aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <EyeOff className="h-5 w-5"/> : <Eye className="h-5 w-5"/>}
                </button>
              </div>
            </label>

            {/* Remember / Forgot */}
            <div className="flex items-center justify-between px-1">
              <label className="flex cursor-pointer items-center gap-2">
                <input type="checkbox" className="h-4 w-4 rounded"
                  style={{ accentColor: isDark ? "#f97316" : "#3b82f6" }} />
                <span className="text-sm" style={{ color: isDark ? "#71717a" : "#64748b" }}>
                  Remember me
                </span>
              </label>
              <button type="button" className="text-sm font-semibold"
                style={{ color: isDark ? "#fb923c" : "#2563eb" }}>
                Forgot password?
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-2xl p-3 text-sm" style={{
                background: isDark ? "rgba(127,29,29,0.3)" : "#fef2f2",
                border: isDark ? "1px solid rgba(185,28,28,0.4)" : "1px solid #fecaca",
                color: isDark ? "#fca5a5" : "#b91c1c",
              }}>
                {error}
              </div>
            )}

            {/* Submit */}
            <button type="submit" disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-full py-4 text-lg font-bold transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70"
              style={{
                background: isDark ? "linear-gradient(to right, #FF6B00, #FFAA00)" : "#3b82f6",
                color: isDark ? "#0a0a0a" : "#ffffff",
                boxShadow: isDark
                  ? "0 0 36px rgba(255,107,0,0.5), 0 2px 12px rgba(0,0,0,0.4)"
                  : "0 4px 24px rgba(59,130,246,0.4)",
              }}>
              {isLoading ? "Signing in..." : "Login to Dashboard"}
              {!isLoading && <ArrowRight className="h-5 w-5"/>}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t"
                style={{ borderColor: isDark ? "rgba(255,255,255,0.07)" : "#e2e8f0" }} />
            </div>
            <div className="relative flex justify-center text-xs font-bold uppercase tracking-[0.18em]">
              <span className="px-4" style={{
                background: isDark ? "rgba(14,12,18,0.82)" : "rgba(255,255,255,0.72)",
                color: isDark ? "#3f3f46" : "#94a3b8",
              }}>
                Or continue with
              </span>
            </div>
          </div>

          {/* Social */}
          <div className="grid grid-cols-2 gap-4">
            {["Google","Apple"].map(provider => (
              <button key={provider} type="button"
                className="flex items-center justify-center gap-3 rounded-full py-3 text-sm font-bold shadow-sm transition-all hover:scale-[1.02]"
                style={{
                  background: isDark ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.75)",
                  border: isDark ? "1px solid rgba(255,255,255,0.08)" : "1px solid #e2e8f0",
                  color: isDark ? "#e4e4e7" : "#1e293b",
                }}>
                {provider}
              </button>
            ))}
          </div>

          {/* Sign up */}
          <p className="mt-10 text-center text-sm" style={{ color: isDark ? "#52525b" : "#64748b" }}>
            Don't have an account?{" "}
            <button type="button" className="font-bold underline underline-offset-4" style={{
              color: isDark ? "#e4e4e7" : "#0f172a",
              textDecorationColor: isDark ? "rgba(251,146,60,0.55)" : "rgba(59,130,246,0.5)",
            }}>
              Start 30-day trial
            </button>
          </p>
        </div>

        {/* Footer */}
        <div className="mt-8 flex flex-wrap justify-center gap-6 text-xs font-bold uppercase tracking-[0.18em]">
          {["Privacy Policy","Terms of Service","Contact Support"].map(link => (
            <button key={link} type="button"
              style={{ color: isDark ? "#3f3f46" : "#94a3b8" }}
              onMouseEnter={e => { e.currentTarget.style.color = isDark ? "#d4d4d8" : "#334155"; }}
              onMouseLeave={e => { e.currentTarget.style.color = isDark ? "#3f3f46" : "#94a3b8"; }}>
              {link}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
