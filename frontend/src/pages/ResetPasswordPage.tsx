import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Eye, EyeOff, KeyRound, Lock } from "lucide-react";
import api from "@/lib/api";
import { SilkBackdrop } from "@/components/backdrop/SilkBackdrop";
import { AuthCard, authInputClass, AuthSubmitButton } from "@/components/auth/AuthCard";
import { PasswordRules, passwordProblems } from "@/components/auth/PasswordRules";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const problems = passwordProblems(password);
  const mismatch = confirm.length > 0 && confirm !== password;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await api.post("/auth/reset-password", { reset_token: token, new_password: password });
      setDone(true);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "That reset link is not valid any more. Request a new one.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (done) {
    return (
      <div className="relative isolate flex min-h-screen w-full items-center justify-center overflow-hidden px-4 py-10">
        <SilkBackdrop />
        <AuthCard title="Password updated" subtitle="Sign in with your new password.">
          <p className="mb-6 rounded-2xl border border-[#C9D9E6] bg-[#EAF1F1] p-3 text-sm text-[#2E3645]">
            Every other session for this account has been signed out.
          </p>
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="w-full rounded-full bg-[#1F5468] py-4 text-[15px] font-semibold text-white shadow-lg transition hover:bg-[#17485a]"
          >
            Go to sign in
          </button>
        </AuthCard>
      </div>
    );
  }

  return (
    <div className="relative isolate flex min-h-screen w-full items-center justify-center overflow-hidden px-4 py-10">
      <SilkBackdrop />
      <AuthCard title="Set a new password" subtitle="Paste the reset token and choose a new password.">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative">
            <KeyRound className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#4A6272]" />
            <input
              type="text"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Reset token"
              className={authInputClass}
            />
          </div>

          <div className="relative">
            <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#4A6272]" />
            <input
              type={showPassword ? "text" : "password"}
              required
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New password"
              className={authInputClass}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-[#4A6272]"
            >
              {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>

          <div className="relative">
            <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#4A6272]" />
            <input
              type={showPassword ? "text" : "password"}
              required
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Confirm new password"
              className={authInputClass}
            />
          </div>

          <PasswordRules password={password} />

          {mismatch && (
            <p className="px-1 text-sm text-[#9d3730]">The two passwords do not match.</p>
          )}

          {error && (
            <div role="alert" className="rounded-2xl border border-[#fecaca] bg-[#fef2f2] p-3 text-sm text-[#b91c1c]">
              {error}
            </div>
          )}

          <AuthSubmitButton
            isLoading={isLoading}
            disabled={problems.length > 0 || mismatch || confirm.length === 0}
            label="Set new password"
            loadingLabel="Saving…"
          />

          <button
            type="button"
            onClick={() => navigate("/login")}
            className="mx-auto flex items-center gap-2 text-sm font-semibold text-[#1F5468] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" /> Back to sign in
          </button>
        </form>
      </AuthCard>
    </div>
  );
}

export default ResetPasswordPage;
