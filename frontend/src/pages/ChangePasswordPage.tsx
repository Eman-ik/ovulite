import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Lock } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { getRoleLandingPath } from "@/lib/roleRoutes";
import { SilkBackdrop } from "@/components/backdrop/SilkBackdrop";
import { AuthCard, authInputClass, AuthSubmitButton } from "@/components/auth/AuthCard";
import { PasswordRules, passwordProblems } from "@/components/auth/PasswordRules";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  must_change_password?: boolean;
}

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { user, applyTokens } = useAuth();
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const forced = Boolean(user?.must_change_password);
  const problems = passwordProblems(password);
  const mismatch = confirm.length > 0 && confirm !== password;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const res = await api.post<TokenResponse>("/auth/change-password", {
        current_password: current,
        new_password: password,
      });
      // Changing a password ends every other session, including the token
      // this page is holding — the server revokes it. The replacement pair
      // comes back in this response and has to be stored, or the user is
      // immediately logged out by their own password change.
      await applyTokens(res.data.access_token, res.data.refresh_token);
      navigate(getRoleLandingPath(user?.role ?? null));
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not change the password. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative isolate flex min-h-screen w-full items-center justify-center overflow-hidden px-4 py-10">
      <SilkBackdrop />
      <AuthCard
        title={forced ? "Choose a new password" : "Change your password"}
        subtitle={
          forced
            ? "This account is on a temporary password. Set your own to continue."
            : "Your other sessions will be signed out."
        }
      >
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative">
            <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#4A6272]" />
            <input
              type="password"
              required
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              placeholder="Current password"
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

          {mismatch && <p className="px-1 text-sm text-[#9d3730]">The two passwords do not match.</p>}

          {error && (
            <div role="alert" className="rounded-2xl border border-[#fecaca] bg-[#fef2f2] p-3 text-sm text-[#b91c1c]">
              {error}
            </div>
          )}

          <AuthSubmitButton
            isLoading={isLoading}
            disabled={problems.length > 0 || mismatch || confirm.length === 0}
            label="Change password"
            loadingLabel="Saving…"
          />
        </form>
      </AuthCard>
    </div>
  );
}

export default ChangePasswordPage;
