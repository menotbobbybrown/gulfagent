"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { formatDistanceToNow } from "date-fns";

type TaskStatus = "pending" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";

interface Task {
  id: string;
  prompt: string;
  task_type: string;
  status: TaskStatus;
  result: string | null;
  error_message: string | null;
  credits_used: number;
  tokens_used: number;
  source: string;
  created_at: string;
  completed_at: string | null;
}

const STATUS_COLORS: Record<TaskStatus, string> = {
  pending: "text-[#6B7280] bg-[#6B7280]/10 border-[#6B7280]/20",
  running: "text-[#3B82F6] bg-[#3B82F6]/10 border-[#3B82F6]/20",
  awaiting_approval: "text-[#F59E0B] bg-[#F59E0B]/10 border-[#F59E0B]/20",
  completed: "text-[#10B981] bg-[#10B981]/10 border-[#10B981]/20",
  failed: "text-[#EF4444] bg-[#EF4444]/10 border-[#EF4444]/20",
  cancelled: "text-[#6B7280] bg-[#6B7280]/10 border-[#6B7280]/20",
};

export default function TasksPage() {
  const searchParams = useSearchParams();
  const automationIdParam = searchParams.get("automation_id");

  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const LIMIT = 20;

  useEffect(() => {
    fetchTasks();
  }, [page, statusFilter, automationIdParam]);

  async function fetchTasks() {
    setLoading(true);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const params = new URLSearchParams({ page: String(page), limit: String(LIMIT) });
      if (statusFilter) params.set("status", statusFilter);
      if (automationIdParam) params.set("automation_id", automationIdParam);

      const res = await fetch(`/api/tasks?${params}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const body = await res.json();
        setTasks(body.data);
        setTotal(body.meta.total);
      }
    } finally {
      setLoading(false);
    }
  }

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-[#E5E0D8]">Task History</h1>
          <p className="text-sm text-[#555] mt-1">{total} total tasks</p>
        </div>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-[#111111] border border-[#242424] text-sm text-[#888] rounded-lg px-3 py-2 outline-none focus:border-[#D4A84B]/40 transition-colors"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton h-16 rounded-xl" />)}
        </div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-16 text-sm text-[#555]">No tasks found.</div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="bg-[#111111] border border-[#1E1E1E] hover:border-[#2A2A2A] rounded-xl overflow-hidden cursor-pointer transition-colors"
              onClick={() => setExpandedId(expandedId === task.id ? null : task.id)}
            >
              <div className="px-4 py-3 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[#C8C0B4] truncate">{task.prompt}</p>
                  <p className="text-xs text-[#444] mt-0.5">
                    {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })} · {task.source} · {task.credits_used} cr
                  </p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-md border font-medium flex-shrink-0 ${STATUS_COLORS[task.status]}`}>
                  {task.status}
                </span>
              </div>

              {expandedId === task.id && (
                <div className="px-4 pb-4 border-t border-[#1A1A1A] pt-3 animate-fade-in">
                  {task.result && (
                    <p className="text-sm text-[#888] whitespace-pre-wrap leading-relaxed">{task.result}</p>
                  )}
                  {task.error_message && (
                    <p className="text-xs text-red-400">{task.error_message}</p>
                  )}
                  <p className="text-xs text-[#3A3A3A] mt-2 font-mono">ID: {task.id}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="px-3 py-1.5 text-xs bg-[#111111] border border-[#242424] text-[#666] hover:text-[#E5E0D8] rounded-lg disabled:opacity-30 transition-colors"
          >
            Previous
          </button>
          <span className="text-xs text-[#444]">
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            className="px-3 py-1.5 text-xs bg-[#111111] border border-[#242424] text-[#666] hover:text-[#E5E0D8] rounded-lg disabled:opacity-30 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
