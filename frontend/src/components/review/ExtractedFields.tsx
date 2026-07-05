"use client";

import { fieldLabel, formatRupees } from "@/lib/utils";
import { ExtractedField } from "@/types";

function ConfidenceBar({ value }: { value: number | null }) {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 80 ? "bg-clean" : pct >= 50 ? "bg-medium" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400">{pct}%</span>
    </div>
  );
}

export default function ExtractedFields({ fields }: { fields: ExtractedField[] }) {
  const populated = fields.filter((f) => f.normalised_value);
  return (
    <div className="divide-y divide-gray-100">
      {populated.map((field) => (
        <div key={field.id} className="flex items-center justify-between gap-3 py-2">
          <div className="min-w-0">
            <p className="text-xs text-gray-400">{fieldLabel(field.field_name)}</p>
            <p className="truncate text-sm font-medium">
              {field.field_name.startsWith("amount") && field.field_name !== "amount_in_words"
                ? formatRupees(field.normalised_value)
                : field.normalised_value}
            </p>
          </div>
          <ConfidenceBar value={field.confidence} />
        </div>
      ))}
    </div>
  );
}
