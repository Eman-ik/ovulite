import { Check, X } from "lucide-react";

/**
 * The password policy, shown as it is typed.
 *
 * These rules mirror backend/app/auth/password_policy.py exactly. The backend
 * is what enforces them — this only saves the user a round trip, so if the two
 * ever disagree the server still wins and the form shows its 422.
 */

const RULES: { label: string; ok: (p: string) => boolean }[] = [
  { label: "At least 8 characters", ok: (p) => p.length >= 8 },
  { label: "An uppercase letter", ok: (p) => /[A-Z]/.test(p) },
  { label: "A lowercase letter", ok: (p) => /[a-z]/.test(p) },
  { label: "A digit", ok: (p) => /\d/.test(p) },
  { label: "A special character", ok: (p) => /[^A-Za-z0-9]/.test(p) },
];

export function passwordProblems(password: string): string[] {
  if (!password) return RULES.map((r) => r.label);
  return RULES.filter((r) => !r.ok(password)).map((r) => r.label);
}

export function PasswordRules({ password }: { password: string }) {
  if (!password) return null;
  return (
    <ul className="space-y-1 px-1">
      {RULES.map((rule) => {
        const ok = rule.ok(password);
        return (
          <li
            key={rule.label}
            className={`flex items-center gap-2 text-xs ${ok ? "text-[#2E3645]" : "text-[#3F4758]"}`}
          >
            {ok ? (
              <Check className="h-3.5 w-3.5 text-[#35748a]" aria-hidden />
            ) : (
              <X className="h-3.5 w-3.5 text-[#9d3730]" aria-hidden />
            )}
            <span>{rule.label}</span>
            <span className="sr-only">{ok ? "met" : "not met"}</span>
          </li>
        );
      })}
    </ul>
  );
}
