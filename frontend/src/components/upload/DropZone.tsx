"use client";

import { TEXT } from "@/lib/constants";
import { classNames } from "@/lib/utils";
import { DragEvent, useRef, useState } from "react";

export default function DropZone({ onFile }: { onFile: (file: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={classNames(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 text-center transition-colors",
        dragging ? "border-accent bg-blue-50" : "border-gray-300 bg-white hover:border-accent"
      )}
    >
      <span className="text-4xl">📄</span>
      <p className="text-sm font-medium">{TEXT.upload.dropHint}</p>
      <p className="text-xs text-gray-400">{TEXT.upload.fileTypes}</p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
