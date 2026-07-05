import { RISK_COLORS } from "@/lib/constants";
import { classNames } from "@/lib/utils";

export default function Badge({
  label,
  tone = "unknown",
  className,
}: {
  label: string;
  tone?: string;
  className?: string;
}) {
  return (
    <span
      className={classNames(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase",
        RISK_COLORS[tone] ?? RISK_COLORS.unknown,
        className
      )}
    >
      {label}
    </span>
  );
}
