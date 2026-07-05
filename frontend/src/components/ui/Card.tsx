import { classNames } from "@/lib/utils";
import { ReactNode } from "react";

export default function Card({
  children,
  className,
  title,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <div className={classNames("rounded-xl bg-white p-5 shadow-sm", className)}>
      {title && <h3 className="mb-4 text-sm font-semibold text-gray-600">{title}</h3>}
      {children}
    </div>
  );
}
