import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { getRoleLandingPath } from "@/lib/roleRoutes";
import { SilkBackdrop } from "@/components/backdrop/SilkBackdrop";

const inputClass =
  "w-full rounded-full border border-white/70 bg-white/55 py-4 pl-12 pr-12 text-[15px] text-[#0F1B24] " +
  "placeholder:text-[#4A6272] shadow-sm outline-none transition focus:bg-white/80 focus:ring-4 focus:ring-[#1F5468]/20";

export function LoginPage() {
  const navigate = useNavigate();
  const { user, login, isLoading: authLoading } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

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


  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 401) {
        setError("Wrong username or password. Please try again.");
      } else {
        setError(err instanceof Error ? err.message : "Login failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative isolate flex min-h-screen w-full items-center justify-center overflow-hidden px-4 py-10">
      <SilkBackdrop />
      <div
        className="relative z-10 w-full max-w-[500px] rounded-[36px] p-8 sm:p-10 md:p-12"
        style={{
          background: "rgba(255, 255, 255, 0.3)",
          backdropFilter: "blur(22px) saturate(140%)",
          WebkitBackdropFilter: "blur(22px) saturate(140%)",
          border: "1px solid rgba(255, 255, 255, 0.6)",
          boxShadow:
            "0 24px 60px -18px rgba(31, 84, 104, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.7)",
        }}
      >
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-[36px] font-medium tracking-tight text-[#0F1B24]">Log in</h1>
          <button
            type="button"
            onClick={() => navigate("/signup")}
            className="text-[15px] font-semibold text-[#1F5468] hover:underline"
          >
            Sign up
          </button>
        </div>

        {user && (
          <div className="mb-5 flex items-center justify-between gap-3 rounded-2xl border border-white/70 bg-white/60 px-4 py-3 text-sm text-[#2E3645]">
            <span>
              Signed in as <strong>{user.username}</strong>.
            </span>
            <button
              type="button"
              onClick={() => navigate(getRoleLandingPath(user.role))}
              className="font-semibold text-[#1F5468] hover:underline"
            >
              Continue
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="relative block">
            <span className="sr-only">Email or username</span>
            <Mail className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#1F5468]" />
            <input
              id="email"
              type="text"
              required
              autoComplete="username"
              placeholder="Email or username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className={inputClass}
            />
          </label>

          <label className="relative block">
            <span className="sr-only">Password</span>
            <Lock className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#1F5468]" />
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              required
              autoComplete="current-password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
            <button
              type="button"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-5 top-1/2 -translate-y-1/2 text-[#1F5468]"
            >
              {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </label>

          <div className="flex justify-end px-1">
            <button type="button" className="text-sm font-semibold text-[#1F5468] hover:underline">
              Forgot password?
            </button>
          </div>

          {error && (
            <div role="alert" className="rounded-2xl border border-[#fecaca] bg-[#fef2f2] p-3 text-sm text-[#b91c1c]">
              {error}
            </div>
          )}

          <button
            id="loginBtn"
            type="submit"
            disabled={isLoading}
            className="mt-2 flex w-full items-center justify-center rounded-full bg-[#0F1B24] py-4 text-[16px] font-semibold text-white shadow-[0_12px_30px_-8px_rgba(15,27,36,0.6)] transition hover:bg-[#1B2C38] disabled:opacity-60"
          >
            {isLoading ? "Signing in..." : "Log in"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
