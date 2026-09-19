import ovuliteLogo from "./icon.png";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Lock, Mail, Moon, Sun, User, CheckCircle } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { GoogleAuthButton } from "@/components/GoogleAuthButton";

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
      <div className="pointer-events-none absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 0%, #0B2B26 0%, #071F1C 40%, #030F10 100%)", zIndex: 0 }} />
      <div className="spotlight-beam pointer-events-none absolute" style={{ top: "-6%", right: "10%", width: 420, height: "110vh", transformOrigin: "50% 0%", background: "conic-gradient(from -6deg at 50% 0%, transparent 0deg, rgba(143,212,166,0.06) 8deg, rgba(114,201,143,0.13) 14deg, rgba(143,212,166,0.06) 20deg, transparent 28deg)", filter: "blur(6px)", zIndex: 2 }} />
      <div className="spotlight-beam pointer-events-none absolute" style={{ top: "-4%", right: "16%", width: 180, height: "100vh", transformOrigin: "50% 0%", background: "linear-gradient(to bottom, rgba(172,223,189,0.28) 0%, rgba(114,201,143,0.10) 35%, rgba(99,196,131,0.03) 70%, transparent 100%)", clipPath: "polygon(30% 0%, 70% 0%, 100% 100%, 0% 100%)", filter: "blur(3px)", zIndex: 3, animationDelay: "0.3s" }} />
      
      {/* Stars */}
      <svg className="pointer-events-none absolute inset-0 h-full w-full" style={{ zIndex: 1 }} xmlns="http://www.w3.org/2000/svg">
        {[[8,4,1.2,2.1],[18,9,0.8,3.4],[34,3,1.5,1.8],[52,7,1.0,4.2],[67,2,0.7,2.8],[80,11,1.3,1.5],[91,5,0.9,3.9],[12,18,1.1,2.5],[27,14,1.4,1.2],[43,20,0.6,4.6],[58,16,1.2,3.1],[74,8,0.8,2.3],[88,19,1.0,1.7],[5,28,0.7,4.8],[22,32,1.3,2.0],[39,25,0.9,3.5],[55,30,1.5,1.4],[71,22,0.6,4.1],[85,27,1.1,2.7],[96,15,0.8,3.3]]
          .map(([cx, cy, r, delay], i) => (
            <circle key={i} cx={`${cx}%`} cy={`${cy}%`} r={r} fill="white" style={{ animation: `starTwinkle ${2.5 + delay * 0.4}s ease-in-out infinite`, animationDelay: `${delay}s`, opacity: 0.7 }} />
          ))}
      </svg>

      {/* Fog & Smoke Layers */}
      <div className="fog-layer-1 pointer-events-none absolute bottom-0 left-0 right-0" style={{ height: "28%", background: "linear-gradient(to top, rgba(19,51,30,0.65) 0%, rgba(26,69,40,0.35) 40%, transparent 100%)", filter: "blur(18px)", zIndex: 2 }} />
      <div className="fog-layer-2 pointer-events-none absolute" style={{ bottom: "20%", left: "-10%", width: "70%", height: "22%", background: "radial-gradient(ellipse at 40% 60%, rgba(50,110,70,0.28) 0%, rgba(28,72,43,0.12) 60%, transparent 100%)", filter: "blur(28px)", zIndex: 2 }} />
      <div className="fog-layer-3 pointer-events-none absolute" style={{ top: "28%", right: "-5%", width: "55%", height: "18%", background: "radial-gradient(ellipse at 60% 40%, rgba(63,78,72,0.22) 0%, rgba(43,57,52,0.08) 60%, transparent 100%)", filter: "blur(32px)", zIndex: 2 }} />

      <div className="smoke-rise pointer-events-none absolute" style={{ bottom: "10%", left: "8%", width: 180, height: 260, background: "radial-gradient(ellipse at 50% 80%, rgba(48,93,63,0.22) 0%, transparent 70%)", filter: "blur(22px)", zIndex: 2 }} />
      <div className="smoke-rise pointer-events-none absolute" style={{ bottom: "8%", right: "18%", width: 140, height: 200, background: "radial-gradient(ellipse at 50% 80%, rgba(36,74,49,0.18) 0%, transparent 70%)", filter: "blur(20px)", zIndex: 2, animationDelay: "7s" }} />
    </>
  );
}


export function SignupPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isDark, setIsDark] = useState(true);
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
  const inputStyle = { background: "#ffffff", border: "1px solid rgba(35,83,71,0.28)", color: "#051F20" };

  const onFocusInput = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.boxShadow = "0 0 0 4px rgba(147,177,166,0.35)";
    e.currentTarget.style.borderColor = "rgba(41,77,64,0.55)";
  };
  const onBlurInput = (e: React.FocusEvent<HTMLInputElement>) => {
    e.currentTarget.style.boxShadow = "none";
    e.currentTarget.style.borderColor = "rgba(41,77,64,0.28)";
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
        {isDark ? <Sun className="h-4 w-4 text-[#8EB69B]" /> : <Moon className="h-4 w-4 text-[#235347]" />}
      </button>

      {/* Split Layout */}
      <div className="flex min-h-screen w-full overflow-hidden">
        {/* LEFT SIDE - Decorative Panel */}
        <div
          className="relative hidden md:flex md:w-1/2 overflow-hidden flex-col justify-end"
          style={{ background: "linear-gradient(135deg, #235347 0%, #2F6D5C 40%, #163832 70%, #051F20 100%)" }}
        >
          {!isDark && (
            <>
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
        </div>

        {/* RIGHT SIDE - Signup Form */}
        <div className="flex w-full md:w-1/2 items-center justify-center px-6 py-8" style={{
          background: isDark ? "#051F20" : "linear-gradient(to bottom, #f2f7f3 0%, #dfeee4 60%, #f2f7f3 100%)",
          transition: "background 0.5s ease",
        }}>
          <div className="w-full max-w-[680px] rounded-[2rem] p-8 md:p-12 backdrop-blur-3xl transition-all duration-500" style={{
            background: isDark ? "rgba(13,17,16,0.82)" : "rgba(255,255,255,0.72)",
            border: isDark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(255,255,255,0.88)",
            boxShadow: isDark ? "0 8px 64px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.06)" : "0 8px 48px rgba(163,220,182,0.2)",
          }}>
            {/* Header */}
            <div className="mb-10 flex flex-col items-center gap-4 text-center">
              <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border-2 shadow-xl" style={{
                borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.9)",
                background: isDark ? "rgba(0,0,0,0.5)" : "#ffffff",
                boxShadow: isDark ? "0 0 24px rgba(70,185,108,0.2)" : undefined,
              }}>
                <img src={ovuliteLogo} alt="Ovulite logo" className="h-full w-full object-cover" />
              </div>

              <div className="rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-[0.16em]" style={{
                background: isDark ? "rgba(70,185,108,0.12)" : "rgba(255,255,255,0.8)",
                border: isDark ? "1px solid rgba(70,185,108,0.3)" : "1px solid rgba(255,255,255,0.8)",
                color: isDark ? "#8EB69B" : "#5c7268",
              }}>
                Create Account
              </div>

              <div>
                <h1 className="mb-2 text-[38px] md:text-[39px] font-bold tracking-tight" style={{ color: isDark ? "#DAF1DE" : "#051F20", fontFamily: '"Plus Jakarta Sans", "Poppins", sans-serif' }}>
                  Join Ovulite
                </h1>
                <p className="text-sm font-medium" style={{ color: isDark ? "#7d9a89" : "#5c7268", fontSize: "14px", fontFamily: '"Inter", sans-serif', fontWeight: 400 }}>
                  Create your account to access the reproductive intelligence platform.
                </p>
              </div>
            </div>

            {success && (
              <div className="mb-6 flex items-center gap-3 rounded-2xl p-4" style={{
                background: isDark ? "rgba(147,177,166,0.16)" : "#eef5f0",
                border: isDark ? "1px solid rgba(147,177,166,0.4)" : "1px solid #8EB69B",
              }}>
                <CheckCircle className="h-5 w-5" style={{ color: isDark ? "#8EB69B" : "#235347" }} />
                <span style={{ color: isDark ? "#8EB69B" : "#235347" }}>Account created successfully! Redirecting to login...</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Full Name */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#c6dccd" : "#051F20" }}>Full Name</span>
                <div className="relative">
                  <User className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#5c7268" }} />
                  <input type="text" required placeholder="John Doe" value={fullName} onChange={(e) => setFullName(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={inputBase} style={inputStyle} />
                </div>
              </label>

              {/* Email */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#c6dccd" : "#051F20" }}>Email Address</span>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#5c7268" }} />
                  <input type="email" required placeholder="name@company.com" value={email} onChange={(e) => setEmail(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={inputBase} style={inputStyle} />
                </div>
              </label>

              {/* Password */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#c6dccd" : "#051F20" }}>Password</span>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#5c7268" }} />
                  <input type={showPassword ? "text" : "password"} required placeholder="Min. 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={`${inputBase} pr-12`} style={inputStyle} />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#5c7268" }}>
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </label>

              {/* Confirm Password */}
              <label className="block">
                <span className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider" style={{ color: isDark ? "#c6dccd" : "#051F20" }}>Confirm Password</span>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#5c7268" }} />
                  <input type={showConfirmPassword ? "text" : "password"} required placeholder="Confirm password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} onFocus={onFocusInput} onBlur={onBlurInput} className={`${inputBase} pr-12`} style={inputStyle} />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-4 top-1/2 -translate-y-1/2" style={{ color: isDark ? "#7d9a89" : "#5c7268" }}>
                    {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </label>

              {/* Terms */}
              <label className="flex cursor-pointer items-center gap-2">
                <input type="checkbox" checked={agreedToTerms} onChange={(e) => setAgreedToTerms(e.target.checked)} className="h-4 w-4 rounded" style={{ accentColor: isDark ? "#8EB69B" : "#235347" }} />
                <span className="text-sm" style={{ color: isDark ? "#7d9a89" : "#5c7268" }}>
                  I agree to the <button type="button" className="underline" style={{ color: isDark ? "#DAF1DE" : "#051F20", fontWeight: 600 }}>Terms and Conditions</button>
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
                background: isDark ? "linear-gradient(to right, #8EB69B, #B6D9C0)" : "#235347",
                color: isDark ? "#051F20" : "#DAF1DE",
                boxShadow: isDark ? "0 0 36px rgba(147,177,166,0.45), 0 2px 12px rgba(0,0,0,0.4)" : "0 10px 30px rgba(10,27,21,0.28)",
              }}>
                {isLoading ? "Creating Account..." : "Create Account"}
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

            <p className="mt-8 text-center text-sm" style={{ color: isDark ? "#7d9a89" : "#5c7268" }}>
              Already have an account?{" "}
              <button type="button" onClick={() => navigate("/login")} className="font-bold underline underline-offset-4" style={{ color: isDark ? "#DAF1DE" : "#051F20" }}>
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