"use client";

import Badge from "@/components/ui/Badge";
import { TEXT } from "@/lib/constants";
import { timeAgo } from "@/lib/utils";
import { Document } from "@/types";
import Link from "next/link";

export default function RecentFlags({ documents }: { documents: Document[] }) {
  if (documents.length === 0) {
    return <p className="py-6 text-center text-sm text-gray-500">{TEXT.dashboard.noFlags}</p>;
  }
  return (
    <ul className="divide-y divide-gray-100">
      {documents.map((doc) => (
        <li key={doc.id}>
          <Link
            href={`/review/${doc.id}`}
            className="flex items-center justify-between gap-3 py-3 hover:bg-gray-50"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">
                {doc.original_filename ?? "Invoice"}
              </p>
              <p className="text-xs text-gray-400">{timeAgo(doc.created_at)}</p>
            </div>
            <Badge label={doc.risk_level} tone={doc.risk_level} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
