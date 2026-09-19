import ovuliteLogo from "./icon.png";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Lock, Mail, Moon, Sun } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { GoogleAuthButton } from "@/components/GoogleAuthButton";


import { getRoleLandingPath } from "@/lib/roleRoutes";

/* ---------------------------------------------
   Animation styles injected once into <head>
--------------------------------------------- */
const PAGE_STYLES = `
  /* -- Night / smog -- */
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
  @keyframes spotlightSweep {
    0%,100% { transform: rotate(-18deg) scaleX(1);   opacity: 0.92; }
    40%     { transform: rotate(-10deg) scaleX(1.04); opacity: 1;    }
    70%     { transform: rotate(-22deg) scaleX(0.97); opacity: 0.88; }
  }
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
  @keyframes mistFloat {
    0% { transform: translateY(0px) translateX(0px); opacity: 0; }
    5% { opacity: 0.4; }
    50% { transform: translateY(-80px) translateX(var(--drift, 0px)); opacity: 0.6; }
    95% { opacity: 0; }
    100% { transform: translateY(-160px) translateX(var(--drift, 0px)); opacity: 0; }
  }
  .mist-particle { animation: mistFloat 8s ease-in forwards infinite; }

  @keyframes etherealFocus {
    0%   { opacity: 0; filter: blur(30px); letter-spacing: 0.4em; transform: scale(1.05); }
    100% { opacity: 1; filter: blur(0);    letter-spacing: -0.03em; transform: scale(1); }
  }
  @keyframes subtitleFade {
    0%   { opacity: 0; transform: translateY(10px); }
    100% { opacity: 1; transform: translateY(0); }
  }
  .welcome-reveal {
    animation: etherealFocus 2.5s cubic-bezier(0.19, 1, 0.22, 1) forwards;
  }
  .subtitle-reveal {
    opacity: 0;
    animation: subtitleFade 1.5s cubic-bezier(0.19, 1, 0.22, 1) 0.8s forwards;
  }
`;

function NightAtmosphere() {
  return (
    <>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at 30% 0%, #0B2B26 0%, #071F1C 40%, #030F10 100%)",
          zIndex: 0,
        }}
      />

      <div
        className="spotlight-beam pointer-events-none absolute"
        style={{
          top: "-6%",
          right: "10%",
          width: 420,
          height: "110vh",
          transformOrigin: "50% 0%",
          background:
            "conic-gradient(from -6deg at 50% 0%, transparent 0deg, rgba(143,212,166,0.06) 8deg, rgba(114,201,143,0.13) 14deg, rgba(143,212,166,0.06) 20deg, transparent 28deg)",
          filter: "blur(6px)",
          zIndex: 2,
        }}
      />
      <div
        className="spotlight-beam pointer-events-none absolute"
        style={{
          top: "-4%",
          right: "16%",
          width: 180,
          height: "100vh",
          transformOrigin: "50% 0%",
          background:
            "linear-gradient(to bottom, rgba(172,223,189,0.28) 0%, rgba(114,201,143,0.10) 35%, rgba(99,196,131,0.03) 70%, transparent 100%)",
          clipPath: "polygon(30% 0%, 70% 0%, 100% 100%, 0% 100%)",
          filter: "blur(3px)",
          zIndex: 3,
          animationDelay: "0.3s",
        }}
      />
      {[
        { right: "22%", top: "18%", size: 2.5, delay: "0s", dur: "7s" },
        { right: "19%", top: "34%", size: 1.5, delay: "1.2s", dur: "9s" },
        { right: "24%", top: "52%", size: 2.0, delay: "2.5s", dur: "6s" },
        { right: "18%", top: "25%", size: 1.2, delay: "0.8s", dur: "11s" },
        { right: "21%", top: "44%", size: 1.8, delay: "3.1s", dur: "8s" },
      ].map((p, i) => (
        <div
          key={`beam-mote-${i}`}
          className="pointer-events-none absolute rounded-full"
          style={{
            right: p.right,
            top: p.top,
            width: p.size * 2,
            height: p.size * 2,
            background: "rgba(186,229,200,0.7)",
            filter: "blur(1px)",
            animation: `dustFloat ${p.dur} ease-in-out infinite`,
            animationDelay: p.delay,
            zIndex: 4,
          }}
        />
      ))}
      <div
        className="pointer-events-none absolute"
        style={{
          top: 0,
          right: "17%",
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(215,240,231,0.95) 0%, rgba(143,212,166,0.5) 50%, transparent 100%)",
          filter: "blur(4px)",
          zIndex: 5,
        }}
      />

      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        style={{ zIndex: 1 }}
        xmlns="http://www.w3.org/2000/svg"
      >
        {[
          [8, 4, 1.2, 2.1], [18, 9, 0.8, 3.4], [34, 3, 1.5, 1.8], [52, 7, 1.0, 4.2],
          [67, 2, 0.7, 2.8], [80, 11, 1.3, 1.5], [91, 5, 0.9, 3.9], [12, 18, 1.1, 2.5],
          [27, 14, 1.4, 1.2], [43, 20, 0.6, 4.6], [58, 16, 1.2, 3.1], [74, 8, 0.8, 2.3],
          [88, 19, 1.0, 1.7], [5, 28, 0.7, 4.8], [22, 32, 1.3, 2.0], [39, 25, 0.9, 3.5],
          [55, 30, 1.5, 1.4], [71, 22, 0.6, 4.1], [85, 27, 1.1, 2.7], [96, 15, 0.8, 3.3],
        ].map(([cx, cy, r, delay], i) => (
          <circle
            key={i}
            cx={`${cx}%`}
            cy={`${cy}%`}
            r={r}
            fill="white"
            style={{
              animation: `starTwinkle ${2.5 + delay * 0.4}s ease-in-out infinite`,
              animationDelay: `${delay}s`,
              opacity: 0.7,
            }}
          />
        ))}
      </svg>

      <div className="pointer-events-none absolute bottom-0 left-0 right-0" style={{
        height: "38%",
        background: "radial-gradient(ellipse at 50% 100%, rgba(85,190,120,0.22) 0%, rgba(58,152,89,0.1) 40%, transparent 70%)",
        zIndex: 1,
      }} />
      <div className="pointer-events-none absolute bottom-0" style={{
        left: "15%", width: "40%", height: "30%",
        background: "radial-gradient(ellipse at 50% 100%, rgba(92,193,126,0.14) 0%, transparent 70%)",
        zIndex: 1,
      }} />

      <div className="fog-layer-1 pointer-events-none absolute bottom-0 left-0 right-0" style={{
        height: "28%",
        background: "linear-gradient(to top, rgba(19,51,30,0.65) 0%, rgba(26,69,40,0.35) 40%, transparent 100%)",
        filter: "blur(18px)", zIndex: 2,
      }} />
      <div className="fog-layer-2 pointer-events-none absolute" style={{
        bottom: "20%", left: "-10%", width: "70%", height: "22%",
        background: "radial-gradient(ellipse at 40% 60%, rgba(50,110,70,0.28) 0%, rgba(28,72,43,0.12) 60%, transparent 100%)",
        filter: "blur(28px)", zIndex: 2,
      }} />
      <div className="fog-layer-3 pointer-events-none absolute" style={{
        top: "28%", right: "-5%", width: "55%", height: "18%",
        background: "radial-gradient(ellipse at 60% 40%, rgba(63,78,72,0.22) 0%, rgba(43,57,52,0.08) 60%, transparent 100%)",
        filter: "blur(32px)", zIndex: 2,
      }} />

      <div className="smoke-rise pointer-events-none absolute" style={{
        bottom: "10%", left: "8%", width: 180, height: 260,
        background: "radial-gradient(ellipse at 50% 80%, rgba(48,93,63,0.22) 0%, transparent 70%)",
        filter: "blur(22px)", zIndex: 2,
      }} />
      <div className="smoke-rise pointer-events-none absolute" style={{
        bottom: "8%", right: "18%", width: 140, height: 200,
        background: "radial-gradient(ellipse at 50% 80%, rgba(36,74,49,0.18) 0%, transparent 70%)",
        filter: "blur(20px)", zIndex: 2, animationDelay: "7s",
      }} />

      {[
        { left: "12%", top: "55%", size: 3, delay: "0s", dur: "8s" },
        { left: "28%", top: "40%", size: 2, delay: "2s", dur: "11s" },
        { left: "45%", top: "65%", size: 2.5, delay: "4s", dur: "9s" },
        { left: "62%", top: "48%", size: 1.5, delay: "1s", dur: "13s" },
        { left: "78%", top: "58%", size: 2, delay: "5s", dur: "10s" },
        { left: "20%", top: "72%", size: 1.5, delay: "6s", dur: "7s" },
        { left: "55%", top: "33%", size: 2, delay: "2.5s", dur: "14s" },
      ].map((p, i) => (
        <div key={`dust-${i}`} className="pointer-events-none absolute rounded-full" style={{
          left: p.left, top: p.top, width: p.size * 2, height: p.size * 2,
          background: "rgba(114,201,143,0.55)", filter: "blur(1px)",
          animation: `dustFloat ${p.dur} ease-in-out infinite`,
          animationDelay: p.delay, zIndex: 3,
        }} />
      ))}

      <div className="pointer-events-none absolute inset-0" style={{
        zIndex: 4, opacity: 0.045,
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
        backgroundRepeat: "repeat", backgroundSize: "200px 200px",
      }} />

      <div className="pointer-events-none absolute inset-0" style={{
        background: "radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(0,0,0,0.55) 100%)",
        zIndex: 4,
      }} />
    </>
  );
}


export function LoginPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isDark, setIsDark] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const { login, isLoading: authLoading } = useAuth();

  useEffect(() => {
    const saved = localStorage.getItem("ovulite_theme");
    // Dark is the default. Only an explicit stored "light" opts out of it.
    setIsDark(saved ? saved !== "light" : true);
  }, []);

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

  if (user) return <Navigate to={getRoleLandingPath(user.role)} replace />;

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
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || "Login failed. Please check your credentials."
            : "Login failed. Please check your credentials.";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const inputBase = "w-full rounded-full py-4 pl-12 pr-4 text-sm shadow-sm outline-none transition-all";
  const inputStyle = {
    background: "#ffffff",
    border: "1px solid rgba(41,77,64,0.28)",
    color: isDark ? "#051F20" : "#051F20",
  };
  const onFocusInput = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.boxShadow = "0 0 0 4px rgba(147,177,166,0.35)";
    e.currentTarget.style.borderColor = "rgba(41,77,64,0.55)";
    e.currentTarget.style.background = "#ffffff";
  };
  const onBlurInput = (e: React.FocusEvent<HTMLInputElement>) => {
  e.currentTarget.style.boxShadow = "none";
  e.currentTarget.style.borderColor = "rgba(41,77,64,0.28)";
  e.currentTarget.style.background = "#ffffff";
};

  return (
    <>
      {/* Dark mode toggle - fixed at top */}
      <button
        type="button"
        aria-label="Toggle dark mode"
        onClick={() => setIsDark((v) => !v)}
        className="fixed right-5 top-5 z-50 flex h-10 w-10 items-center justify-center rounded-full shadow-md backdrop-blur-md transition-all hover:scale-110 active:scale-95"
        style={{
          background: isDark ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.8)",
          border: isDark ? "1px solid rgba(255,255,255,0.12)" : "1px solid rgba(255,255,255,0.75)",
        }}
      >
        {isDark ? <Sun className="h-4 w-4 text-[#8EB69B]" /> : <Moon className="h-4 w-4 text-[#235347]" />}
      </button>

      {/* Split layout container */}
      <div className="flex min-h-screen w-full overflow-hidden">
        {/* ================= LEFT SIDE (Hidden on mobile) ================= */}
        <div
  className="relative hidden md:flex md:w-1/2 overflow-hidden flex-col justify-end"
  style={{
    background: "linear-gradient(135deg, #235347 0%, #2F6D5C 40%, #163832 70%, #051F20 100%)",
  }}
>
          {!isDark && (
            <>
              {/* Smoky lightning effect layers */}
              <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 20%, rgba(215,240,231,0.08) 0%, transparent 40%)", zIndex: 1 }} />
              <div className="pointer-events-none absolute top-0 left-1/4 w-96 h-96 rounded-full blur-[120px]" style={{ background: "rgba(179,226,195,0.12)", zIndex: 1 }} />
              <div className="pointer-events-none absolute bottom-1/3 right-1/4 w-80 h-80 rounded-full blur-[100px]" style={{ background: "rgba(143,212,166,0.08)", zIndex: 1 }} />
              <div className="pointer-events-none absolute -left-20 -top-20 h-[28rem] w-[28rem] rounded-full blur-[110px]" style={{ background: "rgba(157,218,177,0.15)", zIndex: 1 }} />
              <div className="pointer-events-none absolute bottom-8 right-8 h-[22rem] w-[22rem] rounded-full blur-[90px]" style={{ background: "rgba(128,207,154,0.1)", zIndex: 1 }} />
              
            </>
          )}

          {isDark && <NightAtmosphere />}

          {/* Footer mist effect */}
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-40 overflow-hidden" style={{ zIndex: 5 }}>
            {[...Array(15)].map((_, i) => (
              <div
                key={`mist-${i}`}
                className="mist-particle pointer-events-none absolute rounded-full"
                style={{
                  left: `${(i * 7) % 100}%`,
                  bottom: '0px',
                  width: `${40 + (i * 5) % 60}px`,
                  height: `${40 + (i * 5) % 60}px`,
                  background: `radial-gradient(circle at 35% 35%, rgba(186,229,200,0.6) 0%, rgba(128,207,154,0.2) 50%, transparent 100%)`,
                  filter: 'blur(20px)',
                  '--drift': `${-30 + (i % 3) * 30}px`,
                  animationDelay: `${i * 0.4}s`,
                  animationDuration: `${7 + (i % 3)}s`,
                } as React.CSSProperties}
              />
            ))}
          </div>

          {/* Welcome Back — centered in the green panel */}
          <div
            className="welcome-reveal pointer-events-none absolute inset-0 flex items-center justify-center"
            style={{ zIndex: 10 }}
          >
            <div style={{ textAlign: 'center', padding: '0 48px' }}>
              <h1 style={{
                fontSize: '80px',
                fontWeight: 900,
                color: '#ffffff',
                fontFamily: '"Plus Jakarta Sans", "Poppins", sans-serif',
                letterSpacing: '-0.03em',
                lineHeight: 1.05,
                textShadow: '0 4px 32px rgba(0,0,0,0.4), 0 1px 0 rgba(255,255,255,0.15)',
                margin: 0,
              }}>
                Welcome Back
              </h1>
              <p 
                className="subtitle-reveal"
                style={{
                  marginTop: '16px',
                  fontSize: '16px',
                  color: 'rgba(255,255,255,0.7)',
                  fontFamily: '"Inter", sans-serif',
                  fontWeight: 400,
                  letterSpacing: '0.01em',
                }}
              >
                Access your reproductive intelligence dashboard.
              </p>
            </div>
          </div>
        </div>

        {/* ================= RIGHT SIDE (Login Form) ================= */}
        <div className="flex w-full md:w-1/2 items-center justify-center px-6 py-8" style={{
          background: isDark
            ? "#051F20"
            : "linear-gradient(to bottom, #f2f7f3 0%, #dfeee4 60%, #f2f7f3 100%)",
          transition: "background 0.5s ease",
        }}>
          <div
            className="w-full max-w-[680px] rounded-[2rem] p-8 md:p-12 backdrop-blur-3xl transition-all duration-500"
            style={{
              background: isDark ? "rgba(13,17,16,0.82)" : "rgba(255,255,255,0.72)",
              border: isDark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(255,255,255,0.88)",
              boxShadow: isDark
                ? "0 8px 64px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.06)"
                : "0 8px 48px rgba(163,220,182,0.2)",
            }}>
          <div className="mb-10 flex flex-col items-center gap-4 text-center">
            <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border-2 shadow-xl" style={{
              borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.9)",
              background: isDark ? "rgba(0,0,0,0.5)" : "#ffffff",
              boxShadow: isDark ? "0 0 24px rgba(70,185,108,0.2)" : undefined,
            }}>
              <img src={ovuliteLogo} alt="Ovulite logo" className="h-full w-full object-cover" />
            </div>

          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <label className="block">
              <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#c6dccd" : "#051F20", fontSize: "13px", fontFamily: '"Inter", sans-serif', fontWeight: 500 }}>
                Username or Email Address
              </span>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#FFFFFF" }} />
                <input id="email" type="text" required placeholder="name@company.com" value={username} onChange={(e) => setUsername(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={inputBase} style={{...inputStyle, fontSize: "15px", fontFamily: '"Inter", sans-serif', fontWeight: 400 }} />
              </div>
            </label>

            <label className="block">
              <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#c6dccd" : "#051F20", fontSize: "13px", fontFamily: '"Inter", sans-serif', fontWeight: 500 }}>
                Password
              </span>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#5c7268" }} />
                <input id="password" type={showPassword ? "text" : "password"} required placeholder="" value={password} onChange={(e) => setPassword(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={`${inputBase} pr-12`} style={{...inputStyle, fontSize: "15px", fontFamily: '"Inter", sans-serif', fontWeight: 400 }} />
                <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-4 top-1/2 -translate-y-1/2 transition-colors" style={{ color: isDark ? "#7d9a89" : "#5c7268" }} aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </label>

            <div className="flex items-center justify-between px-1">
              <label className="flex cursor-pointer items-center gap-2">
                <input type="checkbox" className="h-4 w-4 rounded" style={{ accentColor: isDark ? "#8EB69B" : "#235347" }} />
                <span className="text-sm" style={{ color: isDark ? "#7d9a89" : "#5c7268", fontSize: "14px", fontFamily: '"Inter", sans-serif', fontWeight: 400 }}>
                  Remember me
                </span>
              </label>
              <button type="button" className="text-sm font-semibold" style={{ color: isDark ? "#8EB69B" : "#235347", fontSize: "14px", fontFamily: '"Inter", sans-serif', fontWeight: 600 }}>
                Forgot password?
              </button>
            </div>

            {error && (
              <div className="rounded-2xl p-3 text-sm" style={{
                background: isDark ? "rgba(127,29,29,0.3)" : "#fef2f2",
                border: isDark ? "1px solid rgba(185,28,28,0.4)" : "1px solid #fecaca",
                color: isDark ? "#fca5a5" : "#b91c1c",
              }}>
                {error}
              </div>
            )}

            <button id="loginBtn" type="submit" disabled={isLoading} className="flex w-full items-center justify-center gap-2 rounded-full py-4 text-lg font-bold transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70" style={{
              // A bright CTA on a dark page, like the orange one it replaces. The
              // gradient stays in the light half of the ramp so the dark label
              // reads across the whole button rather than only its right end.
              background: isDark ? "linear-gradient(to right, #8EB69B, #B6D9C0)" : "#235347",
              color: isDark ? "#051F20" : "#DAF1DE",
              boxShadow: isDark
                ? "0 0 36px rgba(147,177,166,0.45), 0 2px 12px rgba(0,0,0,0.4)"
                : "0 10px 30px rgba(10,27,21,0.28)",
              fontSize: "16px",
              fontFamily: '"Inter", sans-serif',
              fontWeight: 700,
            }}>
              {isLoading ? "Signing in..." : "Login to Dashboard"}
              {!isLoading && <ArrowRight className="h-5 w-5" />}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1" style={{ background: isDark ? "rgba(255,255,255,0.1)" : "rgba(41,77,64,0.16)" }} />
            <span className="text-xs uppercase tracking-wider" style={{ color: isDark ? "#7d9a89" : "#5c7268" }}>or</span>
            <div className="h-px flex-1" style={{ background: isDark ? "rgba(255,255,255,0.1)" : "rgba(41,77,64,0.16)" }} />
          </div>

          <GoogleAuthButton
            isDark={isDark}
            onLoading={setIsLoading}
            onError={setError}
          />

          <p className="mt-10 text-center text-sm" style={{ color: isDark ? "#7d9a89" : "#5c7268", fontSize: "14px", fontFamily: '"Inter", sans-serif', fontWeight: 400 }}>
            Don't have an account?{" "}
            <button type="button" onClick={() => navigate("/signup")} className="font-bold underline underline-offset-4" style={{
              color: isDark ? "#DAF1DE" : "#051F20",
              
              fontSize: "14px",
              fontFamily: '"Inter", sans-serif',
              fontWeight: 700,
            }}>
              Create an Account
            </button>
          </p>
        </div>
      </div>
    </div>
    </>
  );
}

export default LoginPage;
