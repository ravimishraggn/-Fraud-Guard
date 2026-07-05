"use client";

import PageWrapper from "@/components/layout/PageWrapper";
import DropZone from "@/components/upload/DropZone";
import UploadProgress from "@/components/upload/UploadProgress";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/constants";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type Phase = "idle" | "uploading" | "processing" | "failed";

export default function UploadPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [percent, setPercent] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startPolling = (documentId: string) => {
    setPhase("processing");
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/api/v1/documents/${documentId}/status`);
        if (["REVIEW_REQUIRED", "APPROVED", "REJECTED"].includes(data.status)) {
          if (pollRef.current) clearInterval(pollRef.current);
          router.push(`/review/${documentId}`);
        } else if (data.status === "FAILED") {
          if (pollRef.current) clearInterval(pollRef.current);
          setError(TEXT.upload.failed);
          setPhase("failed");
        }
      } catch {
        // Keep polling — transient network errors shouldn't kill the flow
      }
    }, 3000);
  };

  const handleFile = async (selected: File) => {
    setFile(selected);
    setError(null);
    setPhase("uploading");
    setPercent(0);
    const form = new FormData();
    form.append("file", selected);
    try {
      const { data } = await api.post("/api/v1/documents", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          if (evt.total) setPercent(Math.round((evt.loaded / evt.total) * 100));
        },
      });
      setPercent(100);
      startPolling(data.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || TEXT.upload.uploadError);
      setPhase("failed");
    }
  };

  return (
    <PageWrapper title={TEXT.upload.title}>
      <div className="mx-auto max-w-2xl space-y-4">
        {phase === "idle" || phase === "failed" ? (
          <DropZone onFile={handleFile} />
        ) : (
          file && (
            <UploadProgress
              filename={file.name}
              sizeBytes={file.size}
              percent={percent}
              processing={phase === "processing"}
            />
          )
        )}
        {error && (
          <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-danger">
            {error}
          </div>
        )}
        <p className="text-center text-sm text-gray-500">💬 {TEXT.upload.whatsappHint}</p>
      </div>
    </PageWrapper>
  );
}
