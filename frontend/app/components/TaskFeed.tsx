"use client";

/**
 * T15 — TaskFeed: list of tasks with status badges
 * T16 — Connected to POST /api/tasks via onTaskCreated
 * T18 — Subscribes to SSE /api/tasks/stream for live updates
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { formatDistanceToNow } from "date-fns";

type TaskStatus =
  | "pending"
  | "running"
  | "awaiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

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
  created_at: string;
  completed_at: string | null;
}

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; color: string; dot: string; animate: boolean }
> = {
  pending: { label: "Pending", color: "text-[#6B7280]", dot: "bg-[#6B7280]", animate: false },
  running: { label: "Running", color: "text-[#3B82F6]", dot: "bg-[#3B82F6]", animate: true },
  awaiting_approval: { label: "Needs Approval", color: "text-[#F59E0B]", dot: "bg-[#F59E0B]", animate: true },
  completed: { label: "Completed", color: "text-[#10B981]", dot: "bg-[#10B981]", animate: false },
  failed: { label: "Failed", color: "text-[#EF4444]", dot: "bg-[#EF4444]", animate: false },
  cancelled: { label: "Cancelled", color: "text-[#6B7280]", dot: "bg-[#6B7280]", animate: false },
};

const TYPE_ICONS: Record<string, string> = {
  simple: "◆",
  browser: "◉",
  whatsapp: "◈",
  automation: "◎",
};

interface TaskFeedProps {
  newTaskId?: string | null;
}

export function TaskFeed({ newTaskId }: TaskFeedProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sseConnected, setSseConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const tokenRef = useRef<string | null>(null);

  // Fetch initial token
  useEffect(() => {
    createClient().auth.getSession().then(({ data: { session } }) => {
      tokenRef.current = session?.access_token ?? null;
    });
  }, []);

  // SSE subscription (T18)
  useEffect(() => {
    async function connectSSE() {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      tokenRef.current = session.access_token;

      // SSE with auth token in query param (EventSource doesn't support headers)
      const url = `/api/tasks/stream?token=${encodeURIComponent(session.access_token)}`;
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.addEventListener("snapshot", (e) => {
        const data: Task[] = JSON.parse(e.data);
        setTasks(data);
        setLoading(false);
        setSseConnected(true);
      });

      es.addEventListener("task_update", (e) => {
        const updated: Task = JSON.parse(e.data);
        setTasks((prev) => {
          const exists = prev.find((t) => t.id === updated.id);
          if (exists) {
            return prev.map((t) => (t.id === updated.id ? updated : t));
          }
          return [updated, ...prev];
        });
      });

      es.onerror = () => {
        setSseConnected(false);
        es.close();
        // Reconnect after 5s
        setTimeout(connectSSE, 5_000);
      };
    }

    connectSSE();
    return () => eventSourceRef.current?.close();
  }, []);

  // When a new task is created, scroll to top
  useEffect(() => {
    if (newTaskId) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [newTaskId]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-20 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!tasks.length) {
    return (
      <div className="text-center py-16">
        <div className="w-12 h-12 rounded-xl bg-[#1A1A1A] border border-[#242424] flex items-center justify-center mx-auto mb-4 text-xl">
          ◆
        </div>
        <p className="text-sm text-[#555]">No tasks yet. Submit one above to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* SSE status indicator */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs text-[#555] uppercase tracking-wide font-medium">
          Recent Tasks
        </span>
        <div className="flex items-center gap-1.5">
          <div
            className={`w-1.5 h-1.5 rounded-full ${sseConnected ? "bg-[#10B981]" : "bg-[#EF4444]"}`}
          />
          <span className="text-xs text-[#444]">
            {sseConnected ? "Live" : "Reconnecting…"}
          </span>
        </div>
      </div>

      {tasks.map((task) => {
        const cfg = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.pending;
        const isExpanded = expandedId === task.id;
        const isNew = task.id === newTaskId;

        return (
          <div
            key={task.id}
            className={`bg-[#111111] border rounded-xl overflow-hidden transition-all duration-200 cursor-pointer group
              ${isNew ? "border-[#D4A84B]/30 animate-fade-in" : "border-[#1E1E1E] hover:border-[#2A2A2A]"}`}
            onClick={() => setExpandedId(isExpanded ? null : task.id)}
          >
            <div className="px-4 py-3 flex items-start gap-3">
              {/* Type icon */}
              <span className="text-[#333] text-xs mt-0.5 font-mono">
                {TYPE_ICONS[task.task_type] ?? "◆"}
              </span>

              {/* Main content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[#C8C0B4] leading-snug line-clamp-2 group-hover:text-[#E5E0D8] transition-colors">
                  {task.prompt}
                </p>
                <div className="flex items-center gap-3 mt-1.5">
                  <div className="flex items-center gap-1.5">
                    <div
                      className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${cfg.animate ? "status-running" : ""}`}
                    />
                    <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
                  </div>
                  <span className="text-xs text-[#3A3A3A]">·</span>
                  <span className="text-xs text-[#444]">
                    {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                  </span>
                  {task.credits_used > 0 && (
                    <>
                      <span className="text-xs text-[#3A3A3A]">·</span>
                      <span className="text-xs text-[#444]">
                        {task.credits_used} cr
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Detail link + chevron */}
              <div className="flex items-center gap-1 flex-shrink-0 mt-0.5">
                <Link
                  href={`/dashboard/tasks/${task.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-[#333] hover:text-[#D4A84B] p-1"
                  title="View detail"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6h8M6 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </Link>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  className={`text-[#333] transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                >
                  <path d="M3 5l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>

            {/* Expanded result */}
            {isExpanded && (
              <div className="px-4 pb-4 animate-fade-in">
                <div className="border-t border-[#1A1A1A] pt-3">
                  {task.status === "running" && (
                    <div className="flex items-center gap-2 text-xs text-[#3B82F6]">
                      <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Agent is working…
                    </div>
                  )}
                  {task.status === "pending" && (
                    <p className="text-xs text-[#555]">Queued — starting soon…</p>
                  )}
                  {task.result && (
                    <div className="text-sm text-[#A8A09A] leading-relaxed whitespace-pre-wrap font-body">
                      {task.result}
                    </div>
                  )}
                  {task.error_message && (
                    <div className="text-xs text-red-400 bg-red-400/5 rounded-lg p-3 border border-red-400/10">
                      {task.error_message}
                    </div>
                  )}
                  {(task.tokens_used > 0 || task.credits_used > 0) && (
                    <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[#1A1A1A]">
                      <span className="text-xs text-[#3A3A3A]">
                        {task.tokens_used.toLocaleString()} tokens · {task.credits_used} credits used
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
