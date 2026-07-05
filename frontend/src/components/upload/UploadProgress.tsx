"use client";

import { TEXT } from "@/lib/constants";

export default function UploadProgress({
  filename,
  sizeBytes,
  percent,
  processing,
}: {
  filename: string;
  sizeBytes: number;
  percent: number;
  processing: boolean;
}) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <p className="truncate text-sm font-medium">{filename}</p>
        <p className="text-xs text-gray-400">{(sizeBytes / 1024 / 1024).toFixed(2)} MB</p>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
      {processing && (
        <div className="mt-4 flex items-center gap-3">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <div>
            <p className="text-sm font-medium">{TEXT.upload.processing}</p>
            <p className="text-xs text-gray-400">{TEXT.upload.processingHint}</p>
          </div>
        </div>
      )}
    </div>
  );
}
