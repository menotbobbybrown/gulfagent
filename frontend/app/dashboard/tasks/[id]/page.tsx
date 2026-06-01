"use client";

/**
 * T26 — Task detail page: screenshots, steps, result replay
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { formatDistanceToNow, format } from "date-fns";

type TaskStatus = "pending" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";

interface BrowserStep {
  step_number: number;
  action: string;
  description: string;
  url: string | null;
  screenshot_url: string | null;
}

interface Task {
  id: string;
  prompt: string;
  task_type: string;
  status: TaskStatus;
  result: string | null;
  error_message: string | null;
  tokens_used: number;
  credits_used: number;
  source: string;
  metadata: {
    steps?: BrowserStep[];
    screenshots?: string[];
    browser_success?: boolean;
    browser_error?: string;
    model?: string;
  };
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

const STATUS_CONFIG: Record<TaskStatus, { label: string; color: string }> = {
  pending: { label: "Pending", color: "text-[#6B7280] border-[#6B7280]/30 bg-[#6B7280]/10" },
  running: { label: "Running", color: "text-[#3B82F6] border-[#3B82F6]/30 bg-[#3B82F6]/10" },
  awaiting_approval: { label: "Needs Approval", color: "text-[#F59E0B] border-[#F59E0B]/30 bg-[#F59E0B]/10" },
  completed: { label: "Completed", color: "text-[#10B981] border-[#10B981]/30 bg-[#10B981]/10" },
  failed: { label: "Failed", color: "text-[#EF4444] border-[#EF4444]/30 bg-[#EF4444]/10" },
  cancelled: { label: "Cancelled", color: "text-[#6B7280] border-[#6B7280]/30 bg-[#6B7280]/10" },
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedScreenshot, setSelectedScreenshot] = useState<string | null>(null);
  const [pollingActive, setPollingActive] = useState(false);

  useEffect(() => {
    fetchTask();
  }, [id]);

  // Poll while running
  useEffect(() => {
    if (!task) return;
    if (task.status === "running" || task.status === "pending") {
      setPollingActive(true);
      const interval = setInterval(fetchTask, 3000);
      return () => clearInterval(interval);
    } else {
      setPollingActive(false);
    }
  }, [task?.status]);

  async function fetchTask() {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const res = await fetch(`/api/tasks/${id}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) { setLoading(false); return; }
      const body = await res.json();
      setTask(body.data);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        <div className="skeleton h-8 w-48 rounded-lg" />
        <div className="skeleton h-32 rounded-xl" />
        <div className="skeleton h-64 rounded-xl" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 text-center">
        <p className="text-sm text-[#555]">Task not found.</p>
        <button onClick={() => router.back()} className="text-xs text-[#D4A84B] mt-4 hover:underline">
          ← Go back
        </button>
      </div>
    );
  }

  const cfg = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.pending;
  const steps = task.metadata?.steps ?? [];
  const screenshots = task.metadata?.screenshots?.filter(Boolean) ?? [];
  const duration =
    task.started_at && task.completed_at
      ? Math.round((new Date(task.completed_at).getTime() - new Date(task.started_at).getTime()) / 1000)
      : null;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-xs text-[#555] hover:text-[#888] mb-6 transition-colors"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M8 2L4 6l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Back to tasks
      </button>

      {/* Header */}
      <div className="bg-[#111111] border border-[#242424] rounded-2xl p-5 mb-4">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h1 className="font-display text-lg font-semibold text-[#E5E0D8] leading-snug flex-1">
            {task.prompt}
          </h1>
          <span className={`text-xs px-2.5 py-1 rounded-lg border font-medium flex-shrink-0 ${cfg.color}`}>
            {pollingActive && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-current mr-1.5 animate-pulse" />
            )}
            {cfg.label}
          </span>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-[#555]">
          <span className="flex items-center gap-1">
            <span className="text-[#333]">Type</span>
            <span className="text-[#888] capitalize">{task.task_type}</span>
          </span>
          <span>·</span>
          <span className="flex items-center gap-1">
            <span className="text-[#333]">Source</span>
            <span className="text-[#888] capitalize">{task.source}</span>
          </span>
          <span>·</span>
          <span>{format(new Date(task.created_at), "d MMM yyyy, HH:mm")}</span>
          {duration !== null && (
            <>
              <span>·</span>
              <span>{duration}s runtime</span>
            </>
          )}
        </div>

        {/* Stats */}
        <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-[#1A1A1A]">
          {[
            { label: "Tokens", value: task.tokens_used.toLocaleString() },
            { label: "Credits", value: task.credits_used.toLocaleString() },
            { label: "Steps", value: steps.length || "—" },
            { label: "Screenshots", value: screenshots.length || "—" },
            ...(task.metadata?.model ? [{ label: "Model", value: task.metadata.model }] : []),
          ].map(({ label, value }) => (
            <div key={label} className="bg-[#0A0A0A] border border-[#1A1A1A] rounded-lg px-3 py-1.5">
              <span className="text-[#3A3A3A] text-xs">{label}: </span>
              <span className="text-[#888] text-xs font-mono">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Result */}
      {task.result && (
        <div className="bg-[#111111] border border-[#242424] rounded-2xl p-5 mb-4">
          <h2 className="text-xs font-medium text-[#555] uppercase tracking-wide mb-3">Result</h2>
          <div className="text-sm text-[#C8C0B4] leading-relaxed whitespace-pre-wrap font-body">
            {task.result}
          </div>
        </div>
      )}

      {/* Error */}
      {task.error_message && (
        <div className="bg-red-950/20 border border-red-500/20 rounded-2xl p-5 mb-4">
          <h2 className="text-xs font-medium text-red-400/70 uppercase tracking-wide mb-2">Error</h2>
          <p className="text-sm text-red-400">{task.error_message}</p>
        </div>
      )}

      {/* Browser steps */}
      {steps.length > 0 && (
        <div className="bg-[#111111] border border-[#242424] rounded-2xl p-5 mb-4">
          <h2 className="text-xs font-medium text-[#555] uppercase tracking-wide mb-4">
            Browser Steps ({steps.length})
          </h2>
          <div className="space-y-2">
            {steps.map((step) => (
              <div
                key={step.step_number}
                className="flex items-start gap-3 group"
              >
                {/* Step number */}
                <div className="w-6 h-6 rounded-md bg-[#1A1A1A] border border-[#242424] flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[10px] font-mono text-[#444]">{step.step_number}</span>
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[#888] leading-snug truncate">{step.action || step.description}</p>
                  {step.url && (
                    <p className="text-xs text-[#444] font-mono truncate mt-0.5">{step.url}</p>
                  )}
                </div>

                {/* Screenshot thumbnail */}
                {step.screenshot_url && (
                  <button
                    onClick={() => setSelectedScreenshot(step.screenshot_url!)}
                    className="flex-shrink-0 w-16 h-10 rounded-md overflow-hidden border border-[#2A2A2A] hover:border-[#D4A84B]/40 transition-colors"
                  >
                    <img
                      src={step.screenshot_url}
                      alt={`Step ${step.step_number}`}
                      className="w-full h-full object-cover object-top"
                    />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Screenshot gallery */}
      {screenshots.length > 0 && (
        <div className="bg-[#111111] border border-[#242424] rounded-2xl p-5">
          <h2 className="text-xs font-medium text-[#555] uppercase tracking-wide mb-4">
            Screenshots ({screenshots.length})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {screenshots.map((url, i) => (
              <button
                key={i}
                onClick={() => setSelectedScreenshot(url)}
                className="aspect-video rounded-lg overflow-hidden border border-[#1E1E1E] hover:border-[#D4A84B]/40 transition-colors"
              >
                <img
                  src={url}
                  alt={`Screenshot ${i + 1}`}
                  className="w-full h-full object-cover object-top"
                  loading="lazy"
                />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Screenshot lightbox */}
      {selectedScreenshot && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
          onClick={() => setSelectedScreenshot(null)}
        >
          <div className="relative max-w-5xl w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setSelectedScreenshot(null)}
              className="absolute -top-10 right-0 text-[#888] hover:text-[#E5E0D8] text-xs"
            >
              Close ✕
            </button>
            <img
              src={selectedScreenshot}
              alt="Screenshot"
              className="w-full rounded-xl border border-[#2A2A2A] shadow-2xl"
            />
          </div>
        </div>
      )}
    </div>
  );
}
