"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";

interface OrchestratorStatus {
  available_routes: string[];
  cost_today_usd: number;
  cost_month_usd: number;
  most_used_model: string | null;
  avg_latency: number | null;
  fallback_rate: number | null;
  total_calls: number | null;
}

interface UserRow {
  id: string;
  email: string;
  tier: string;
  is_admin: boolean;
  created_at: string | null;
}

interface TestResult {
  result: string;
  model_used: string;
  cost_usd: number;
  latency_ms: number;
  error: string | null;
}

export default function AdminPage() {
  const [status, setStatus] = useState<OrchestratorStatus | null>(null);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [testPrompt, setTestPrompt] = useState("");
  const [testTaskType, setTestTaskType] = useState("simple_qa");
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [adminLoading, setAdminLoading] = useState(true);

  const getToken = useCallback(async () => {
    const { data: { session } } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  }, []);

  // Check admin status and fetch data
  useEffect(() => {
    async function init() {
      try {
        const token = await getToken();
        if (!token) {
          setIsAdmin(false);
          setAdminLoading(false);
          return;
        }
        // Try to fetch admin data — 403 means not admin
        const statusRes = await fetch("/api/admin/orchestrator/status", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!statusRes.ok) {
          setIsAdmin(false);
          setAdminLoading(false);
          return;
        }
        setIsAdmin(true);
        const { data: statusData } = await statusRes.json();
        setStatus(statusData);

        // Fetch users
        const usersRes = await fetch("/api/admin/users", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (usersRes.ok) {
          const { data: usersData } = await usersRes.json();
          setUsers(usersData ?? []);
        }
      } catch {
        setIsAdmin(false);
      } finally {
        setAdminLoading(false);
      }
    }
    init();
  }, [getToken]);

  async function handleTest(e: React.FormEvent) {
    e.preventDefault();
    if (!testPrompt.trim() || testLoading) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch("/api/admin/orchestrator/test", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ prompt: testPrompt.trim(), task_type: testTaskType }),
      });
      if (res.ok) {
        const { data } = await res.json();
        setTestResult(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setTestLoading(false);
    }
  }

  async function handleMakeAdmin(userId: string) {
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`/api/admin/users/${userId}/make-admin`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_admin: true } : u));
      }
    } catch (err) {
      console.error(err);
    }
  }

  if (adminLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-[#D4A84B]/20 border-t-[#D4A84B] rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="bg-[#111111] border border-[#242424] rounded-2xl p-8 text-center">
          <h1 className="font-display text-2xl font-semibold text-[#E5E0D8] mb-3">Access Denied</h1>
          <p className="text-sm text-[#666]">Admin access required to view this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-[#E5E0D8]">Admin Dashboard</h1>
        <p className="text-sm text-[#666]">Orchestrator status, user management, and tools.</p>
      </div>

      {/* Orchestrator Status */}
      <section>
        <h2 className="text-xs font-bold text-[#D4A84B] uppercase tracking-widest mb-4 border-b border-[#D4A84B]/10 pb-2">
          Orchestrator Status
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatusCard label="Routes Available" value={status?.available_routes?.length ?? 0} />
          <StatusCard label="Cost Today (USD)" value={`$${(status?.cost_today_usd ?? 0).toFixed(4)}`} />
          <StatusCard label="Cost This Month (USD)" value={`$${(status?.cost_month_usd ?? 0).toFixed(4)}`} />
          <StatusCard label="Total Calls" value={status?.total_calls ?? 0} />
          <StatusCard label="Most Used Model" value={status?.most_used_model ?? "—"} />
          <StatusCard label="Avg Latency (ms)" value={status?.avg_latency ? `${Math.round(status.avg_latency)}ms` : "—"} />
          <StatusCard label="Fallback Rate" value={status?.fallback_rate != null ? `${(status.fallback_rate * 100).toFixed(1)}%` : "—"} />
        </div>
      </section>

      {/* Test Orchestrator */}
      <section>
        <h2 className="text-xs font-bold text-[#D4A84B] uppercase tracking-widest mb-4 border-b border-[#D4A84B]/10 pb-2">
          Test Orchestrator
        </h2>
        <div className="bg-[#111111] border border-[#242424] rounded-2xl p-5">
          <form onSubmit={handleTest} className="space-y-4">
            <div>
              <label className="block text-xs text-[#555] mb-1">Task Type</label>
              <select
                value={testTaskType}
                onChange={(e) => setTestTaskType(e.target.value)}
                className="w-full sm:w-64 bg-[#0A0A0A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-sm text-[#E5E0D8] outline-none focus:border-[#D4A84B]/40"
              >
                {status?.available_routes?.map(route => (
                  <option key={route} value={route}>{route}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#555] mb-1">Prompt</label>
              <textarea
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder="Enter a test prompt…"
                className="w-full bg-[#0A0A0A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-sm text-[#E5E0D8] outline-none focus:border-[#D4A84B]/40 min-h-[80px] resize-y"
                rows={3}
              />
            </div>
            <button
              type="submit"
              disabled={testLoading || !testPrompt.trim()}
              className="bg-[#D4A84B] hover:bg-[#C49A35] disabled:opacity-30 text-[#0A0A0A] text-sm font-semibold rounded-lg px-4 py-2 transition-all"
            >
              {testLoading ? "Running…" : "Run Test"}
            </button>
          </form>

          {testResult && (
            <div className="mt-4 bg-[#0A0A0A] border border-[#1E1E1E] rounded-xl p-4 space-y-2">
              <div className="flex flex-wrap gap-4 text-xs text-[#888]">
                <span>Model: <span className="text-[#D4A84B]">{testResult.model_used || "—"}</span></span>
                <span>Cost: <span className="text-[#D4A84B]">${testResult.cost_usd?.toFixed(6) ?? "0"}</span></span>
                <span>Latency: <span className="text-[#D4A84B]">{testResult.latency_ms ?? 0}ms</span></span>
              </div>
              {testResult.error ? (
                <p className="text-xs text-red-400">Error: {testResult.error}</p>
              ) : (
                <p className="text-sm text-[#C8C0B4] whitespace-pre-wrap">{testResult.result}</p>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Users Table */}
      <section>
        <h2 className="text-xs font-bold text-[#D4A84B] uppercase tracking-widest mb-4 border-b border-[#D4A84B]/10 pb-2">
          Users
        </h2>
        <div className="bg-[#111111] border border-[#242424] rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#1A1A1A] text-[#555] text-xs uppercase tracking-wide">
                  <th className="text-left px-5 py-3 font-medium">Email</th>
                  <th className="text-left px-5 py-3 font-medium">Tier</th>
                  <th className="text-left px-5 py-3 font-medium">Admin</th>
                  <th className="text-left px-5 py-3 font-medium">Created</th>
                  <th className="text-left px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1A1A1A]">
                {users.map(u => (
                  <tr key={u.id} className="text-[#C8C0B4] hover:bg-[#0A0A0A] transition-colors">
                    <td className="px-5 py-3">{u.email}</td>
                    <td className="px-5 py-3 capitalize">{u.tier}</td>
                    <td className="px-5 py-3">
                      {u.is_admin ? (
                        <span className="text-[#10B981]">Yes</span>
                      ) : (
                        <span className="text-[#555]">No</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-[#666] text-xs">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-5 py-3">
                      {!u.is_admin && (
                        <button
                          onClick={() => handleMakeAdmin(u.id)}
                          className="text-xs text-[#D4A84B] hover:text-[#C49A35] border border-[#D4A84B]/20 hover:border-[#D4A84B]/40 rounded-lg px-3 py-1 transition-all"
                        >
                          Make Admin
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-[#555]">No users found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

function StatusCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-[#111111] border border-[#242424] rounded-xl p-4">
      <p className="text-[10px] text-[#555] uppercase tracking-wide font-medium mb-1">{label}</p>
      <p className="text-lg font-semibold text-[#E5E0D8]">{value}</p>
    </div>
  );
}