"use client";

import { SEVERITY_COLORS, SEVERITY_ICONS, TEXT } from "@/lib/constants";
import { classNames } from "@/lib/utils";
import { FraudFlag } from "@/types";
import Link from "next/link";

export default function FraudFlagCard({ flag }: { flag: FraudFlag }) {
  const matchedDocId = flag.evidence?.matched_document_id as string | undefined;
  return (
    <div
      className={classNames(
        "rounded-lg border p-4",
        SEVERITY_COLORS[flag.severity] ?? SEVERITY_COLORS.low
      )}
    >
      <p className="text-sm font-bold">
        {SEVERITY_ICONS[flag.severity]} {flag.severity.toUpperCase()} — {flag.title}
      </p>
      <p className="mt-2 text-sm text-gray-700">{flag.description}</p>
      {matchedDocId && (
        <Link
          href={`/review/${matchedDocId}`}
          className="mt-2 inline-block text-sm font-medium text-accent hover:underline"
        >
          {TEXT.detail.viewMatching} →
        </Link>
      )}
    </div>
  );
}
