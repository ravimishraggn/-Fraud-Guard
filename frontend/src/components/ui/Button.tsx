"use client";

import { classNames } from "@/lib/utils";
import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "success" | "danger" | "secondary" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-blue-600",
  success: "bg-clean text-white hover:bg-green-700",
  danger: "bg-danger text-white hover:bg-red-700",
  secondary: "bg-white border border-gray-300 text-navy hover:bg-gray-50",
  ghost: "text-accent hover:bg-blue-50",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

export default function Button({
  variant = "primary",
  loading = false,
  className,
  children,
  disabled,
  ...rest
}: Props) {
  return (
    <button
      className={classNames(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
      )}
      {children}
    </button>
  );
}
