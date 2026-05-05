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
      "bg-[#00483D] text-white shadow-[0_8px_16px_rgba(0,72,61,0.4)] hover:brightness-110",
    destructive: "bg-[#00483D] text-white shadow-[0_8px_16px_rgba(0,72,61,0.4)] hover:brightness-110",
    outline:
      "border border-[rgba(255,255,255,0.24)] bg-[#00483D] text-white shadow-[0_8px_16px_rgba(0,72,61,0.4)] hover:brightness-110",
    secondary: "bg-[#00483D] text-white shadow-[0_8px_16px_rgba(0,72,61,0.4)] hover:brightness-110",
    ghost: "bg-[#00483D] text-white shadow-[0_8px_16px_rgba(0,72,61,0.4)] hover:brightness-110",
    link: "bg-[#00483D] text-white shadow-[0_8px_16px_rgba(0,72,61,0.4)] hover:brightness-110",
  },
  size: {
    default: "h-10 px-4 py-2 text-sm sm:text-base",
    sm: "h-8 sm:h-9 rounded-md px-2 sm:px-3 text-xs sm:text-sm",
    lg: "h-10 sm:h-11 rounded-md px-4 sm:px-8 text-sm sm:text-base",
    icon: "h-9 w-9 sm:h-10 sm:w-10",
  },
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-lg !text-white text-[10px] sm:text-xs font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 touch-manipulation hover:scale-[1.25] hover:-translate-y-1 hover:shadow-[0_16px_32px_rgba(0,72,61,0.5),0_0_20px_rgba(0,72,61,0.3)]",
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
