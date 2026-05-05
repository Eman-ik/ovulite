import ovuliteLogo from "./icon.png";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Lock, Mail, Moon, Sun, User, CheckCircle } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

import api from "@/lib/api";

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

  @keyframes bubbleFloat {
    0%   { transform: translateY(0px)    translateX(0px)   rotate(0deg); }
    25%  { transform: translateY(-35px)  translateX(10px)  rotate(6deg); }
    50%  { transform: translateY(-18px)  translateX(-8px)  rotate(-4deg); }
    75%  { transform: translateY(-45px)  translateX(12px)  rotate(5deg); }
    100% { transform: translateY(0px)    translateX(0px)   rotate(0deg); }
  }
  @keyframes bubbleShimmer {
    0%,100% { opacity: 0.55; }
    50%     { opacity: 0.80; }
  }
  .bubble { animation: bubbleFloat   var(--dur,10s) ease-in-out infinite var(--delay,0s),
                       bubbleShimmer var(--sdur,6s) ease-in-out infinite var(--sdelay,0s); }
  @keyframes mistFloat {
    0% { transform: translateY(0px) translateX(0px); opacity: 0; }
    5% { opacity: 0.4; }
    50% { transform: translateY(-80px) translateX(var(--drift, 0px)); opacity: 0.6; }
    95% { opacity: 0; }
    100% { transform: translateY(-160px) translateX(var(--drift, 0px)); opacity: 0; }
  }
  .mist-particle { animation: mistFloat 8s ease-in forwards infinite; }
`;

function NightAtmosphere() {
  return (
    <>
      <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 0%, #1a0f2e 0%, #0a0a14 40%, #050508 100%)", zIndex: 0 }} />
      <div className="spotlight-beam pointer-events-none absolute" style={{ top: "-6%", right: "10%", width: 420, height: "110vh", transformOrigin: "50% 0%", background: "conic-gradient(from -6deg at 50% 0%, transparent 0deg, rgba(255,200,100,0.06) 8deg, rgba(255,180,60,0.13) 14deg, rgba(255,200,100,0.06) 20deg, transparent 28deg)", filter: "blur(6px)", zIndex: 2 }} />
      <div className="spotlight-beam pointer-events-none absolute" style={{ top: "-4%", right: "16%", width: 180, height: "100vh", transformOrigin: "50% 0%", background: "linear-gradient(to bottom, rgba(255,220,140,0.28) 0%, rgba(255,180,60,0.10) 35%, rgba(255,140,40,0.03) 70%, transparent 100%)", clipPath: "polygon(30% 0%, 70% 0%, 100% 100%, 0% 100%)", filter: "blur(3px)", zIndex: 3, animationDelay: "0.3s" }} />
      
      {/* Stars */}
      <svg className="pointer-events-none absolute inset-0 h-full w-full" style={{ zIndex: 1 }} xmlns="http://www.w3.org/2000/svg">
        {[[8,4,1.2,2.1],[18,9,0.8,3.4],[34,3,1.5,1.8],[52,7,1.0,4.2],[67,2,0.7,2.8],[80,11,1.3,1.5],[91,5,0.9,3.9],[12,18,1.1,2.5],[27,14,1.4,1.2],[43,20,0.6,4.6],[58,16,1.2,3.1],[74,8,0.8,2.3],[88,19,1.0,1.7],[5,28,0.7,4.8],[22,32,1.3,2.0],[39,25,0.9,3.5],[55,30,1.5,1.4],[71,22,0.6,4.1],[85,27,1.1,2.7],[96,15,0.8,3.3]]
          .map(([cx, cy, r, delay], i) => (
            <circle key={i} cx={`${cx}%`} cy={`${cy}%`} r={r} fill="white" style={{ animation: `starTwinkle ${2.5 + delay * 0.4}s ease-in-out infinite`, animationDelay: `${delay}s`, opacity: 0.7 }} />
          ))}
      </svg>

      {/* Fog & Smoke Layers */}
      <div className="fog-layer-1 pointer-events-none absolute bottom-0 left-0 right-0" style={{ height: "28%", background: "linear-gradient(to top, rgba(60,30,10,0.65) 0%, rgba(80,40,15,0.35) 40%, transparent 100%)", filter: "blur(18px)", zIndex: 2 }} />
      <div className="fog-layer-2 pointer-events-none absolute" style={{ bottom: "20%", left: "-10%", width: "70%", height: "22%", background: "radial-gradient(ellipse at 40% 60%, rgba(120,80,40,0.28) 0%, rgba(80,50,20,0.12) 60%, transparent 100%)", filter: "blur(28px)", zIndex: 2 }} />
      <div className="fog-layer-3 pointer-events-none absolute" style={{ top: "28%", right: "-5%", width: "55%", height: "18%", background: "radial-gradient(ellipse at 60% 40%, rgba(60,60,80,0.22) 0%, rgba(40,40,60,0.08) 60%, transparent 100%)", filter: "blur(32px)", zIndex: 2 }} />

      <div className="smoke-rise pointer-events-none absolute" style={{ bottom: "10%", left: "8%", width: 180, height: 260, background: "radial-gradient(ellipse at 50% 80%, rgba(100,70,40,0.22) 0%, transparent 70%)", filter: "blur(22px)", zIndex: 2 }} />
      <div className="smoke-rise pointer-events-none absolute" style={{ bottom: "8%", right: "18%", width: 140, height: 200, background: "radial-gradient(ellipse at 50% 80%, rgba(80,60,30,0.18) 0%, transparent 70%)", filter: "blur(20px)", zIndex: 2, animationDelay: "7s" }} />
    </>
  );
}

const BUBBLES = [
  { size: 90, left: "6%", top: "12%", dur: "11s", delay: "0s", sdur: "7s", sdelay: "0s" },
  { size: 54, left: "82%", top: "8%", dur: "14s", delay: "2s", sdur: "9s", sdelay: "1s" },
  { size: 120, left: "70%", top: "42%", dur: "9s", delay: "0.5s", sdur: "6s", sdelay: "3s" },
  { size: 40, left: "3%", top: "55%", dur: "13s", delay: "3s", sdur: "8s", sdelay: "1.5s" },
  { size: 70, left: "14%", top: "76%", dur: "10s", delay: "1.5s", sdur: "11s", sdelay: "0.5s" },
  { size: 48, left: "72%", top: "70%", dur: "16s", delay: "4s", sdur: "7s", sdelay: "2s" },
  { size: 30, left: "55%", top: "5%", dur: "12s", delay: "1s", sdur: "9s", sdelay: "4s" },
  { size: 80, left: "40%", top: "82%", dur: "8s", delay: "2.5s", sdur: "6s", sdelay: "0s" },
  { size: 35, left: "86%", top: "22%", dur: "15s", delay: "0s", sdur: "10s", sdelay: "2.5s" },
  { size: 60, left: "25%", top: "18%", dur: "11s", delay: "3.5s", sdur: "8s", sdelay: "1s" },
];

function GlassBubbles() {
  return (
    <>
      {BUBBLES.map((b, i) => (
        <div key={i} className="bubble pointer-events-none absolute" style={{
          left: b.left, top: b.top, width: b.size, height: b.size, borderRadius: "50%",
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
          "--dur": b.dur,
          "--delay": b.delay,
          "--sdur": b.sdur,
          "--sdelay": b.sdelay,
        } as React.CSSProperties}>
          <div style={{ position: "absolute", top: "14%", left: "18%", width: "30%", height: "14%", borderRadius: "50%", background: "rgba(255,255,255,0.85)", filter: "blur(2px)", transform: "rotate(-30deg)" }} />
          <div style={{ position: "absolute", bottom: "18%", right: "14%", width: "22%", height: "10%", borderRadius: "50%", background: "rgba(180,220,255,0.55)", filter: "blur(3px)", transform: "rotate(20deg)" }} />
        </div>
      ))}
    </>
  );
}

export function SignupPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isDark, setIsDark] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("ovulite_theme");
    setIsDark(saved ? saved === "dark" : false);
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

  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (!agreedToTerms) {
      setError("You must agree to the terms and conditions");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setIsLoading(true);
    try {
      await api.post("/auth/register", {
        username: email,
        email: email,
        password: password,
        full_name: fullName,
      });
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message :
        typeof err === "object" && err !== null && "response" in err
          ? (err as any).response?.data?.detail || "Signup failed. Please try again."
          : "Signup failed. Please try again.";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const inputBase = "w-full rounded-full py-4 pl-12 pr-4 text-sm shadow-sm outline-none transition-all";
  const inputStyle = { background: "#ffffff", border: "1px solid rgba(31, 77, 68, 0.3)", color: "#1e293b" };

  const onFocusInput = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.boxShadow = "0 0 0 4px rgba(255, 213, 128, 0.3)";
    e.currentTarget.style.borderColor = "rgba(255, 213, 128, 0.5)";
  };
  const onBlurInput = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.boxShadow = "none";
    e.currentTarget.style.borderColor = "rgba(31, 77, 68, 0.3)";
  };

  return (
    <>
      {/* Dark Mode Toggle */}
      <button
        type="button"
        onClick={() => setIsDark((v) => !v)}
        className="fixed right-5 top-5 z-50 flex h-10 w-10 items-center justify-center rounded-full shadow-md backdrop-blur-md transition-all hover:scale-110 active:scale-95"
        style={{
          background: isDark ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.8)",
          border: isDark ? "1px solid rgba(255,255,255,0.12)" : "1px solid rgba(255,255,255,0.75)",
        }}
      >
        {isDark ? <Sun className="h-4 w-4 text-orange-400" /> : <Moon className="h-4 w-4 text-blue-500" />}
      </button>

      {/* Split Layout */}
      <div className="flex min-h-screen w-full overflow-hidden">
        {/* LEFT SIDE - Decorative Panel */}
        <div
          className="relative hidden md:flex md:w-1/2 overflow-hidden flex-col justify-end"
          style={{ background: "linear-gradient(135deg, #1F4D44 0%, #2a6b60 40%, #1a3a33 70%, #0f2420 100%)" }}
        >
          {!isDark && (
            <>
              <div className="absolute inset-0 z-0">
                <GlassBubbles />
              </div>
              <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 20%, rgba(255, 240, 200, 0.08) 0%, transparent 40%)", zIndex: 1 }} />
              <div className="pointer-events-none absolute top-0 left-1/4 w-96 h-96 rounded-full blur-[120px]" style={{ background: "rgba(255, 220, 150, 0.12)", zIndex: 1 }} />
              <div className="pointer-events-none absolute bottom-1/3 right-1/4 w-80 h-80 rounded-full blur-[100px]" style={{ background: "rgba(255, 200, 100, 0.08)", zIndex: 1 }} />
              <div className="pointer-events-none absolute -left-20 -top-20 h-[28rem] w-[28rem] rounded-full blur-[110px]" style={{ background: "rgba(255, 200, 120, 0.15)", zIndex: 1 }} />
              <div className="pointer-events-none absolute bottom-8 right-8 h-[22rem] w-[22rem] rounded-full blur-[90px]" style={{ background: "rgba(255, 180, 80, 0.1)", zIndex: 1 }} />
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
                  background: `radial-gradient(circle at 35% 35%, rgba(255, 220, 160, 0.6) 0%, rgba(255, 180, 80, 0.2) 50%, transparent 100%)`,
                  filter: 'blur(20px)',
                  '--drift': `${-30 + (i % 3) * 30}px`,
                  animationDelay: `${i * 0.4}s`,
                  animationDuration: `${7 + (i % 3)}s`,
                } as React.CSSProperties}
              />
            ))}
          </div>
        </div>

        {/* RIGHT SIDE - Signup Form */}
        <div className="flex w-full md:w-1/2 items-center justify-center px-6 py-8" style={{
          background: isDark ? "#060608" : "linear-gradient(to bottom, #F7F3ED 0%, #D9CDBF 60%, #F7F3ED 100%)",
          transition: "background 0.5s ease",
        }}>
          <div className="w-full max-w-[680px] rounded-[2rem] p-8 md:p-12 backdrop-blur-3xl transition-all duration-500" style={{
            background: isDark ? "rgba(14,12,18,0.82)" : "rgba(255,255,255,0.72)",
            border: isDark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(255,255,255,0.88)",
            boxShadow: isDark ? "0 8px 64px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.06)" : "0 8px 48px rgba(255, 213, 128, 0.2)",
          }}>
            {/* Header */}
            <div className="mb-10 flex flex-col items-center gap-4 text-center">
              <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border-2 shadow-xl" style={{
                borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.9)",
                background: isDark ? "rgba(0,0,0,0.5)" : "#ffffff",
                boxShadow: isDark ? "0 0 24px rgba(255,140,0,0.2)" : undefined,
              }}>
                <img src={ovuliteLogo} alt="Ovulite logo" className="h-full w-full object-cover" />
              </div>

              <div className="rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-[0.16em]" style={{
                background: isDark ? "rgba(255,107,0,0.12)" : "rgba(255,255,255,0.8)",
                border: isDark ? "1px solid rgba(255,107,0,0.3)" : "1px solid rgba(255,255,255,0.8)",
                color: isDark ? "#fb923c" : "#475569",
              }}>
                Create Account
              </div>

              <div>
                <h1 className="mb-2 text-[38px] md:text-[39px] font-bold tracking-tight" style={{ color: isDark ? "#f4f4f5" : "#0f172a", fontFamily: '"Plus Jakarta Sans", "Poppins", sans-serif' }}>
                  Join Ovulite
                </h1>
                <p className="text-sm font-medium" style={{ color: isDark ? "#71717a" : "#64748b", fontSize: "14px", fontFamily: '"Inter", sans-serif', fontWeight: 400 }}>
                  Create your account to access the reproductive intelligence platform.
                </p>
              </div>
            </div>

            {success && (
              <div className="mb-6 flex items-center gap-3 rounded-2xl p-4" style={{
                background: isDark ? "rgba(34,197,94,0.15)" : "#f0fdf4",
                border: isDark ? "1px solid rgba(74,222,128,0.4)" : "1px solid #86efac",
              }}>
                <CheckCircle className="h-5 w-5" style={{ color: isDark ? "#86efac" : "#22c55e" }} />
                <span style={{ color: isDark ? "#86efac" : "#16a34a" }}>Account created successfully! Redirecting to login...</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Full Name */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#d4d4d8" : "#1e293b" }}>Full Name</span>
                <div className="relative">
                  <User className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#52525b" : "#94a3b8" }} />
                  <input type="text" required placeholder="John Doe" value={fullName} onChange={(e) => setFullName(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={inputBase} style={inputStyle} />
                </div>
              </label>

              {/* Email */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#d4d4d8" : "#1e293b" }}>Email Address</span>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#52525b" : "#94a3b8" }} />
                  <input type="email" required placeholder="name@company.com" value={email} onChange={(e) => setEmail(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={inputBase} style={inputStyle} />
                </div>
              </label>

              {/* Password */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#d4d4d8" : "#1e293b" }}>Password</span>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#52525b" : "#94a3b8" }} />
                  <input type={showPassword ? "text" : "password"} required placeholder="Min. 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={`${inputBase} pr-12`} style={inputStyle} />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2" style={{ color: isDark ? "#52525b" : "#94a3b8" }}>
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </label>

              {/* Confirm Password */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#d4d4d8" : "#1e293b" }}>Confirm Password</span>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#52525b" : "#94a3b8" }} />
                  <input type={showConfirmPassword ? "text" : "password"} required placeholder="Confirm password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={`${inputBase} pr-12`} style={inputStyle} />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-4 top-1/2 -translate-y-1/2" style={{ color: isDark ? "#52525b" : "#94a3b8" }}>
                    {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </label>

              {/* Terms */}
              <label className="flex cursor-pointer items-center gap-2">
                <input type="checkbox" checked={agreedToTerms} onChange={(e) => setAgreedToTerms(e.target.checked)} className="h-4 w-4 rounded" style={{ accentColor: isDark ? "#f97316" : "#3b82f6" }} />
                <span className="text-sm" style={{ color: isDark ? "#71717a" : "#64748b" }}>
                  I agree to the <button type="button" className="underline" style={{ color: isDark ? "#e4e4e7" : "#0f172a", fontWeight: 600 }}>Terms and Conditions</button>
                </span>
              </label>

              {error && (
                <div className="rounded-2xl p-3 text-sm" style={{
                  background: isDark ? "rgba(127,29,29,0.3)" : "#fef2f2",
                  border: isDark ? "1px solid rgba(185,28,28,0.4)" : "1px solid #fecaca",
                  color: isDark ? "#fca5a5" : "#b91c1c",
                }}>
                  {error}
                </div>
              )}

              <button type="submit" disabled={isLoading || success} className="flex w-full items-center justify-center gap-2 rounded-full py-4 text-lg font-bold transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70" style={{
                background: isDark ? "linear-gradient(to right, #FF6B00, #FFAA00)" : "#000000",
                color: isDark ? "#0a0a0a" : "#ffffff",
                boxShadow: isDark ? "0 0 36px rgba(255,107,0,0.5), 0 2px 12px rgba(0,0,0,0.4)" : "0 4px 24px rgba(0,0,0,0.25)",
              }}>
                {isLoading ? "Creating Account..." : "Create Account"}
                {!isLoading && <ArrowRight className="h-5 w-5" />}
              </button>
            </form>



            <p className="mt-8 text-center text-sm" style={{ color: isDark ? "#52525b" : "#64748b" }}>
              Already have an account?{" "}
              <button type="button" onClick={() => navigate("/login")} className="font-bold underline underline-offset-4" style={{ color: isDark ? "#e4e4e7" : "#0f172a" }}>
                Sign In
              </button>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

export default SignupPage;