"use client";

import { useState, useRef, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface TaskInputProps {
  onTaskCreated?: (taskId: string) => void;
}

const EXAMPLE_PROMPTS = [
  "Summarize today's Gulf News headlines",
  "Check AED to PKR exchange rate",
  "Draft a follow-up email for a sales prospect",
  "Research competitors in the UAE fintech space",
  "Monitor iPhone 16 price on Noon.com",
];

export function TaskInput({ onTaskCreated }: TaskInputProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [prompt]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("Not authenticated");

      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ prompt: prompt.trim(), source: "dashboard" }),
      });

      if (!res.ok) {
        const body = await res.json();
        const msg =
          body?.detail?.message ??
          body?.detail ??
          body?.error?.message ??
          "Failed to submit task";
        throw new Error(msg);
      }

      const body = await res.json();
      setPrompt("");
      onTaskCreated?.(body.data.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function useExample(example: string) {
    setPrompt(example);
    textareaRef.current?.focus();
  }

  const charCount = prompt.length;
  const isOverLimit = charCount > 10_000;

  return (
    <div className="bg-[#111111] border border-[#242424] rounded-2xl p-4 hover:border-[#2A2A2A] transition-colors">
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit(e);
            }}
            placeholder="What should the agent do? e.g. 'Find the best VAT consultant in Dubai and summarise their services'"
            className="w-full bg-transparent text-sm text-[#E5E0D8] placeholder-[#333] resize-none outline-none leading-relaxed min-h-[72px] pr-2"
            rows={3}
          />
        </div>

        {error && (
          <p className="text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2 mt-3">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#1A1A1A]">
          <span className={`text-xs ${isOverLimit ? "text-red-400" : "text-[#3A3A3A]"}`}>
            {charCount.toLocaleString()} / 10,000
          </span>

          <div className="flex items-center gap-2">
            <span className="hidden sm:block text-xs text-[#333]">⌘↵ to run</span>
            <button
              type="submit"
              disabled={loading || !prompt.trim() || isOverLimit}
              className="flex items-center gap-2 bg-[#D4A84B] hover:bg-[#C49A35] disabled:opacity-30 disabled:cursor-not-allowed text-[#0A0A0A] text-xs font-semibold rounded-lg px-4 py-2 transition-all"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Running…
                </>
              ) : (
                <>
                  Run task
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6h8M6 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Example prompts */}
      {!prompt && (
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLE_PROMPTS.map((ex) => (
            <button
              key={ex}
              onClick={() => useExample(ex)}
              className="text-xs text-[#555] hover:text-[#D4A84B] bg-[#0A0A0A] hover:bg-[#D4A84B]/5 border border-[#1A1A1A] hover:border-[#D4A84B]/20 rounded-lg px-2.5 py-1 transition-all"
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
