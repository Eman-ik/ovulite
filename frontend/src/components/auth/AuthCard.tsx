import type { ReactNode } from "react";

/**
 * The frosted-glass shell the auth screens share.
 *
 * Extracted when the password screens were added rather than copying
 * LoginPage's card a third and fourth time — the glass values, the radius and
 * the backdrop filter were already duplicated between login and signup, and a
 * palette change would have had to find every copy.
 */

export const authInputClass =
  "w-full rounded-full border border-white/70 bg-white/55 py-4 pl-12 pr-12 text-[15px] text-[#0F1B24] " +
  "placeholder:text-[#4A6272] shadow-sm outline-none transition focus:bg-white/80 focus:ring-4 focus:ring-[#1F5468]/20";

export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div
      className="relative z-10 w-full max-w-[500px] rounded-[36px] p-8 sm:p-10 md:p-12"
      style={{
        background: "rgba(255, 255, 255, 0.3)",
        backdropFilter: "blur(22px) saturate(140%)",
        WebkitBackdropFilter: "blur(22px) saturate(140%)",
        border: "1px solid rgba(255, 255, 255, 0.6)",
        boxShadow: "0 24px 60px rgba(31, 84, 104, 0.18)",
      }}
    >
      <div className="mb-7 text-center">
        <h1 className="text-[26px] font-bold tracking-tight text-[#0F1B24]">{title}</h1>
        {subtitle && <p className="mt-2 text-sm text-[#3F4758]">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function AuthSubmitButton({
  isLoading,
  label,
  loadingLabel,
  disabled,
}: {
  isLoading: boolean;
  label: string;
  loadingLabel: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={isLoading || disabled}
      className="w-full rounded-full bg-[#1F5468] py-4 text-[15px] font-semibold text-white shadow-lg transition hover:bg-[#17485a] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {isLoading ? (
        <span className="flex items-center justify-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/60 border-t-transparent" />
          {loadingLabel}
        </span>
      ) : (
        label
      )}
    </button>
  );
}
