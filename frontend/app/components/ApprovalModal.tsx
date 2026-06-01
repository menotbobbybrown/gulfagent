"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Approval {
  id: string;
  task_id: string;
  action_type: string;
  action_payload: Record<string, unknown>;
  expires_at: string;
}

interface ApprovalModalProps {
  approval: Approval;
  onClose: () => void;
  onDecision: (id: string, decision: "approved" | "denied") => void;
}

const ACTION_LABELS: Record<string, string> = {
  email: "Send an Email",
  form_submit: "Submit a Form",
  payment: "Make a Payment",
  file_delete: "Delete a File",
};

const ACTION_ICONS: Record<string, string> = {
  email: "✉️",
  form_submit: "📋",
  payment: "💳",
  file_delete: "🗑️",
};

export function ApprovalModal({ approval, onClose, onDecision }: ApprovalModalProps) {
  const [loading, setLoading] = useState<"approve" | "deny" | null>(null);

  const expiresAt = new Date(approval.expires_at);
  const secondsLeft = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000));

  async function decide(decision: "approved" | "denied") {
    setLoading(decision === "approved" ? "approve" : "deny");
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      await fetch(`/api/approvals/${approval.id}/decide`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ decision }),
      });
      onDecision(approval.id, decision);
    } catch {
      // Silent fail — will auto-deny on timeout
    } finally {
      setLoading(null);
      onClose();
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative bg-[#111111] border border-[#2A2A2A] rounded-2xl p-6 w-full max-w-md shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="flex items-start gap-4 mb-6">
          <div className="w-10 h-10 rounded-xl bg-[#F59E0B]/10 border border-[#F59E0B]/30 flex items-center justify-center text-lg flex-shrink-0">
            {ACTION_ICONS[approval.action_type] ?? "⚡"}
          </div>
          <div>
            <h2 className="font-display text-[#E5E0D8] text-lg font-semibold">
              Approval Required
            </h2>
            <p className="text-sm text-[#888] mt-0.5">
              Agent wants to:{" "}
              <span className="text-[#F59E0B]">
                {ACTION_LABELS[approval.action_type] ?? approval.action_type}
              </span>
            </p>
          </div>
        </div>

        {/* Payload preview */}
        <div className="bg-[#0A0A0A] border border-[#1E1E1E] rounded-lg p-4 mb-4 font-mono text-xs text-[#888] overflow-auto max-h-40">
          <pre>{JSON.stringify(approval.action_payload, null, 2)}</pre>
        </div>

        {/* Timeout warning */}
        <p className="text-xs text-[#555] mb-6">
          Auto-denies in{" "}
          <span className="text-[#F59E0B]">
            {Math.floor(secondsLeft / 60)}m {secondsLeft % 60}s
          </span>{" "}
          if no action taken.
        </p>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => decide("denied")}
            disabled={loading !== null}
            className="flex-1 bg-[#1A1A1A] hover:bg-[#222] border border-[#2A2A2A] text-[#888] hover:text-[#E5E0D8] text-sm font-medium rounded-lg py-2.5 transition-all disabled:opacity-40"
          >
            {loading === "deny" ? "Denying…" : "Deny"}
          </button>
          <button
            onClick={() => decide("approved")}
            disabled={loading !== null}
            className="flex-1 bg-[#D4A84B] hover:bg-[#C49A35] text-[#0A0A0A] text-sm font-semibold rounded-lg py-2.5 transition-all disabled:opacity-40"
          >
            {loading === "approve" ? "Approving…" : "Approve"}
          </button>
        </div>
      </div>
    </div>
  );
}
