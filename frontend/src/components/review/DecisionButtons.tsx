"use client";

import Button from "@/components/ui/Button";
import { TEXT } from "@/lib/constants";
import { useState } from "react";

export default function DecisionButtons({
  onDecision,
  submitting,
}: {
  onDecision: (decision: "approved" | "rejected" | "escalated", note: string) => void;
  submitting: boolean;
}) {
  const [note, setNote] = useState("");

  return (
    <div className="space-y-3">
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder={TEXT.detail.notePlaceholder}
        rows={3}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-accent focus:outline-none"
      />
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button
          variant="success"
          className="flex-1"
          loading={submitting}
          onClick={() => onDecision("approved", note)}
        >
          ✓ {TEXT.detail.approve}
        </Button>
        <Button
          variant="danger"
          className="flex-1"
          loading={submitting}
          onClick={() => onDecision("rejected", note)}
        >
          ✕ {TEXT.detail.reject}
        </Button>
        <Button
          variant="secondary"
          className="flex-1"
          loading={submitting}
          onClick={() => onDecision("escalated", note)}
        >
          ↗ {TEXT.detail.escalate}
        </Button>
      </div>
    </div>
  );
}
