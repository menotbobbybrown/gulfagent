"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

interface Automation {
  id: string;
  name: string;
  prompt: string;
  cron: string;
  active: boolean;
  last_run: string | null;
  next_run: string | null;
  created_at: string;
}

export default function AutomationsPage() {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Form state
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [cron, setCron] = useState("0 8 * * *");
  
  const getToken = useCallback(async () => {
    const { data: { session } } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  }, []);

  const fetchAutomations = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch("/api/automations", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const { data } = await res.json();
        setAutomations(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchAutomations();
  }, [fetchAutomations]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch("/api/automations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name, prompt, cron }),
      });
      if (res.ok) {
        setIsModalOpen(false);
        setName("");
        setPrompt("");
        setCron("0 8 * * *");
        fetchAutomations();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const toggleActive = async (id: string, currentStatus: boolean) => {
    try {
      const token = await getToken();
      if (!token) return;
      await fetch(`/api/automations/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ active: !currentStatus }),
      });
      fetchAutomations();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this automation?")) return;
    try {
      const token = await getToken();
      if (!token) return;
      await fetch(`/api/automations/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchAutomations();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-[#E5E0D8]">Automations</h1>
          <p className="text-sm text-[#666]">Manage your recurring AI tasks.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-[#D4A84B] text-black text-sm font-medium rounded-lg hover:bg-[#C59B3F] transition-colors"
        >
          New Automation
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-[#D4A84B]/20 border-t-[#D4A84B] rounded-full animate-spin" />
        </div>
      ) : automations.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-[#181818] rounded-xl">
          <p className="text-[#666]">No automations yet.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {automations.map((a) => (
            <div key={a.id} className="bg-[#0D0D0D] border border-[#181818] rounded-xl p-5 flex items-center justify-between">
              <div className="flex-1 min-w-0 mr-4">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="font-medium text-[#E5E0D8]">{a.name}</h3>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                    a.active ? 'bg-[#D4A84B]/10 text-[#D4A84B] border-[#D4A84B]/20' : 'bg-[#181818] text-[#444] border-[#222]'
                  }`}>
                    {a.active ? 'ACTIVE' : 'PAUSED'}
                  </span>
                </div>
                <p className="text-sm text-[#666] line-clamp-1 mb-2">{a.prompt}</p>
                <div className="flex items-center gap-4 text-[11px] text-[#444]">
                  <span className="flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor">
                      <circle cx="8" cy="8" r="6" strokeWidth="1.2"/>
                      <path d="M8 4v4l2 2" strokeWidth="1.2"/>
                    </svg>
                    {a.cron}
                  </span>
                  {a.last_run && (
                    <span>Last run: {new Date(a.last_run).toLocaleString()}</span>
                  )}
                  <Link href={`/dashboard/tasks?automation_id=${a.id}`} className="text-[#D4A84B] hover:underline">
                    View History
                  </Link>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleActive(a.id, a.active)}
                  className="p-2 text-[#666] hover:text-[#D4A84B] transition-colors"
                  title={a.active ? "Pause" : "Resume"}
                >
                  {a.active ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="6" y="4" width="4" height="16" rx="1"/>
                      <rect x="14" y="4" width="4" height="16" rx="1"/>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M5 3l14 9-14 9V3z" fill="currentColor"/>
                    </svg>
                  )}
                </button>
                <button
                  onClick={() => handleDelete(a.id)}
                  className="p-2 text-[#666] hover:text-red-500 transition-colors"
                  title="Delete"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" strokeLinecap="round"/>
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
          <div className="bg-[#0D0D0D] border border-[#181818] rounded-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-5 border-b border-[#181818] flex justify-between items-center">
              <h2 className="font-display text-lg font-semibold text-[#E5E0D8]">New Automation</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-[#555] hover:text-[#888]">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-medium text-[#666] uppercase tracking-wider mb-2">Name</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Daily News Brief"
                  className="w-full bg-[#141414] border border-[#181818] rounded-lg px-4 py-2.5 text-sm text-[#E5E0D8] focus:outline-none focus:border-[#D4A84B]/50 transition-colors"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#666] uppercase tracking-wider mb-2">Prompt</label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe what the agent should do..."
                  className="w-full bg-[#141414] border border-[#181818] rounded-lg px-4 py-2.5 text-sm text-[#E5E0D8] focus:outline-none focus:border-[#D4A84B]/50 transition-colors h-32 resize-none"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#666] uppercase tracking-wider mb-2">Schedule (Cron)</label>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {[
                    { label: "Every hour", value: "0 * * * *" },
                    { label: "Daily at 8 AM", value: "0 8 * * *" },
                    { label: "Weekly Mon 9 AM", value: "0 9 * * 1" },
                    { label: "Weekdays 9 AM", value: "0 9 * * 1-5" },
                  ].map((preset) => (
                    <button
                      key={preset.value}
                      type="button"
                      onClick={() => setCron(preset.value)}
                      className={`px-3 py-1.5 text-[11px] rounded border transition-colors ${
                        cron === preset.value ? 'bg-[#D4A84B]/10 text-[#D4A84B] border-[#D4A84B]/20' : 'bg-[#141414] text-[#555] border-[#181818] hover:bg-[#181818]'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
                <input
                  value={cron}
                  onChange={(e) => setCron(e.target.value)}
                  placeholder="0 * * * *"
                  className="w-full bg-[#141414] border border-[#181818] rounded-lg px-4 py-2.5 text-sm text-[#E5E0D8] font-mono focus:outline-none focus:border-[#D4A84B]/50 transition-colors"
                  required
                />
              </div>
              <div className="pt-2 flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2.5 bg-[#141414] text-[#666] text-sm font-medium rounded-lg hover:bg-[#181818] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-[2] px-8 py-2.5 bg-[#D4A84B] text-black text-sm font-medium rounded-lg hover:bg-[#C59B3F] transition-colors"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
