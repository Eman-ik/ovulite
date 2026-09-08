import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const buttonVariants = {
  variant: {
    default:
      "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-[0_1px_2px_rgba(22,24,26,0.08),0_10px_24px_-14px_rgba(22,24,26,0.5)] hover:bg-[#25292d]",
    destructive:
      "bg-[var(--destructive)] text-white shadow-[0_1px_2px_rgba(22,24,26,0.08),0_10px_24px_-14px_rgba(210,86,79,0.6)] hover:brightness-105",
    outline:
      "border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] shadow-[0_1px_2px_rgba(22,24,26,0.05)] hover:bg-black/[0.04]",
    secondary:
      "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:bg-black/[0.07]",
    ghost: "bg-transparent text-[var(--foreground)] hover:bg-black/[0.05]",
    link: "bg-transparent text-[var(--foreground)] underline underline-offset-4 hover:text-[var(--muted-foreground)]",
  },
  size: {
    default: "h-10 px-4 py-2 text-sm",
    sm: "h-8 sm:h-9 rounded-lg px-2 sm:px-3 text-xs",
    lg: "h-10 sm:h-11 rounded-xl px-4 sm:px-8 text-sm",
    icon: "h-9 w-9 sm:h-10 sm:w-10",
  },
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        className={cn(
          "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-xs font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 touch-manipulation hover:-translate-y-px",
          buttonVariants.variant[variant],
          buttonVariants.size[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
