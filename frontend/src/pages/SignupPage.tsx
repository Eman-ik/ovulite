import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, CheckCircle, Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { GoogleAuthButton } from "@/components/GoogleAuthButton";
import { SilkBackdrop } from "@/components/backdrop/SilkBackdrop";
import api from "@/lib/api";

const inputClass =
  "w-full rounded-full border border-white/70 bg-white/55 py-4 pl-12 pr-12 text-[15px] text-[#0F1B24] " +
  "placeholder:text-[#4A6272] shadow-sm outline-none transition focus:bg-white/80 focus:ring-4 focus:ring-[#1F5468]/20";

export function SignupPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
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
  const [signupMessage, setSignupMessage] = useState("");

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
      const res = await api.post<{ message: string; pending_approval: boolean }>(
        "/auth/register",
        {
          username: email,
          email: email,
          password: password,
          full_name: fullName,
        },
      );
      setSuccess(true);
      setSignupMessage(res.data.message);
      // A pending account cannot log in yet, so bouncing to the sign-in form
      // would send the user somewhere that can only refuse them. Leave the
      // message on screen and let them navigate.
      if (!res.data.pending_approval) {
        setTimeout(() => navigate("/login"), 2000);
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || "Signup failed. Please try again."
            : "Signup failed. Please try again.";
      setError(errorMessage);
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
          <h1 className="text-[36px] font-medium tracking-tight text-[#0F1B24]">Sign up</h1>
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="text-[15px] font-semibold text-[#1F5468] hover:underline"
          >
            Log in
          </button>
        </div>

        {user && (
          <div className="mb-5 rounded-2xl border border-white/70 bg-white/60 px-4 py-3 text-sm text-[#051F20]">
            Signed in as <strong>{user.username}</strong>. Creating an account here does not sign you out.
          </div>
        )}

        {success && (
          <div role="status" className="mb-5 flex items-start gap-2 rounded-2xl border border-white/70 bg-white/70 px-4 py-3 text-sm text-[#0F1B24]">
            <CheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-[#1F5468]" />
            {/* The server says whether approval is needed; saying "taking you
                to log in" regardless would promise a sign-in that is refused. */}
            <span>{signupMessage || "Account created. Taking you to log in..."}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="relative block">
            <span className="sr-only">Full name</span>
            <User className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#1F5468]" />
            <input
              type="text"
              required
              autoComplete="name"
              placeholder="Full name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className={inputClass}
            />
          </label>

          <label className="relative block">
            <span className="sr-only">Email address</span>
            <Mail className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#1F5468]" />
            <input
              type="email"
              required
              autoComplete="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </label>

          <label className="relative block">
            <span className="sr-only">Password</span>
            <Lock className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#1F5468]" />
            <input
              type={showPassword ? "text" : "password"}
              required
              autoComplete="new-password"
              placeholder="Password (min. 8 characters)"
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

          <label className="relative block">
            <span className="sr-only">Confirm password</span>
            <Lock className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#1F5468]" />
            <input
              type={showConfirmPassword ? "text" : "password"}
              required
              autoComplete="new-password"
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={inputClass}
            />
            <button
              type="button"
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              onClick={() => setShowConfirmPassword((v) => !v)}
              className="absolute right-5 top-1/2 -translate-y-1/2 text-[#1F5468]"
            >
              {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </label>

          <label className="flex cursor-pointer items-center gap-2 px-1 text-sm text-[#0F1B24]">
            <input
              type="checkbox"
              checked={agreedToTerms}
              onChange={(e) => setAgreedToTerms(e.target.checked)}
              className="h-4 w-4 rounded"
              style={{ accentColor: "#1F5468" }}
            />
            <span>
              I agree to the{" "}
              <button type="button" className="font-semibold text-[#1F5468] underline">
                Terms and Conditions
              </button>
            </span>
          </label>

          {error && (
            <div role="alert" className="rounded-2xl border border-[#fecaca] bg-[#fef2f2] p-3 text-sm text-[#b91c1c]">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || success}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-full bg-[#0F1B24] py-4 text-[16px] font-semibold text-white shadow-[0_12px_30px_-8px_rgba(15,27,36,0.6)] transition hover:bg-[#1B2C38] disabled:opacity-60"
          >
            {isLoading ? "Creating account..." : "Create account"}
            {!isLoading && <ArrowRight className="h-5 w-5" />}
          </button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-[#1F5468]/20" />
          <span className="text-xs uppercase tracking-wider text-[#3F5A66]">or</span>
          <div className="h-px flex-1 bg-[#1F5468]/20" />
        </div>

        <GoogleAuthButton isDark={false} onLoading={setIsLoading} onError={setError} />

        <p className="mt-8 text-center text-sm text-[#3F5A66]">
          Already have an account?{" "}
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="font-bold text-[#0F1B24] underline underline-offset-4"
          >
            Log in
          </button>
        </p>
      </div>
    </div>
  );
}

export default SignupPage;
