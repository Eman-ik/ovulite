import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Mail } from "lucide-react";
import api from "@/lib/api";
import { SilkBackdrop } from "@/components/backdrop/SilkBackdrop";
import { AuthCard, authInputClass, AuthSubmitButton } from "@/components/auth/AuthCard";

interface ForgotPasswordResponse {
  message: string;
  reset_token?: string | null;
}

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [devToken, setDevToken] = useState<string | null>(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setDevToken(null);
    setIsLoading(true);
    try {
      const res = await api.post<ForgotPasswordResponse>("/auth/forgot-password", { email });
      setMessage(res.data.message);
      // The backend returns the token only outside production and only while
      // no mail server is configured. None is, in this deployment, so this is
      // what makes the flow usable at all — rather than pretending an email
      // was sent that nobody will receive.
      setDevToken(res.data.reset_token ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request a reset. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative isolate flex min-h-screen w-full items-center justify-center overflow-hidden px-4 py-10">
      <SilkBackdrop />
      <AuthCard
        title="Reset your password"
        subtitle="Enter the email on your account and we'll send a reset link."
      >
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative">
            <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#4A6272]" />
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              className={authInputClass}
            />
          </div>

          {error && (
            <div role="alert" className="rounded-2xl border border-[#fecaca] bg-[#fef2f2] p-3 text-sm text-[#b91c1c]">
              {error}
            </div>
          )}

          {message && (
            <div className="rounded-2xl border border-[#C9D9E6] bg-[#EAF1F1] p-3 text-sm text-[#2E3645]">
              <p>{message}</p>
              {devToken && (
                <div className="mt-3 border-t border-[#C9D9E6] pt-3">
                  <p className="font-semibold">No mail server is configured on this server.</p>
                  <p className="mt-1">
                    The reset token is shown here so the flow can be completed. It expires shortly
                    and can be used once.
                  </p>
                  <code className="mt-2 block break-all rounded-lg bg-white/80 p-2 font-mono text-xs text-[#2E3645]">
                    {devToken}
                  </code>
                  <button
                    type="button"
                    onClick={() => navigate(`/reset-password?token=${encodeURIComponent(devToken)}`)}
                    className="mt-3 text-sm font-semibold text-[#1F5468] hover:underline"
                  >
                    Continue to set a new password →
                  </button>
                </div>
              )}
            </div>
          )}

          <AuthSubmitButton isLoading={isLoading} label="Send reset link" loadingLabel="Sending…" />

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

export default ForgotPasswordPage;
