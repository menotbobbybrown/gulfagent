"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { useSearchParams } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    if (searchParams.get("error")) {
      setError("Authentication failed. Please try again.");
    }
  }, [searchParams]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    setLoading(false);
    if (authError) {
      setError(authError.message);
    } else {
      setSent(true);
    }
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            "linear-gradient(rgba(212,168,75,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(212,168,75,0.03) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* Radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[radial-gradient(ellipse_at_center,rgba(212,168,75,0.06)_0%,transparent_70%)] pointer-events-none" />

      <div className="relative w-full max-w-sm animate-fade-in">
        {/* Logo mark */}
        <div className="mb-10 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl border border-[#D4A84B]/30 bg-[#D4A84B]/10 mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L3 7v10l9 5 9-5V7L12 2z"
                stroke="#D4A84B"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <path
                d="M12 2v20M3 7l9 5 9-5"
                stroke="#D4A84B"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-display font-semibold text-[#E5E0D8] tracking-tight">
            GulfAgent
          </h1>
          <p className="text-sm text-[#666] mt-1 font-body">
            AI automation for the Gulf
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#111111] border border-[#242424] rounded-2xl p-8">
          {sent ? (
            <div className="text-center py-4 animate-fade-in">
              <div className="w-12 h-12 rounded-full bg-[#D4A84B]/10 border border-[#D4A84B]/30 flex items-center justify-center mx-auto mb-4">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path
                    d="M4 10l4 4 8-8"
                    stroke="#D4A84B"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <h2 className="text-lg font-display text-[#E5E0D8] mb-2">
                Check your inbox
              </h2>
              <p className="text-sm text-[#888] leading-relaxed">
                We sent a magic link to{" "}
                <span className="text-[#D4A84B]">{email}</span>. Click it to
                sign in — no password needed.
              </p>
              <button
                onClick={() => { setSent(false); setEmail(""); }}
                className="mt-6 text-xs text-[#555] hover:text-[#888] transition-colors"
              >
                Use a different email
              </button>
            </div>
          ) : (
            <>
              <h2 className="text-lg font-display text-[#E5E0D8] mb-1">
                Sign in
              </h2>
              <p className="text-sm text-[#666] mb-6">
                Enter your email to receive a magic link
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label
                    htmlFor="email"
                    className="block text-xs font-medium text-[#888] mb-1.5 tracking-wide uppercase"
                  >
                    Email address
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    className="w-full bg-[#0A0A0A] border border-[#2A2A2A] rounded-lg px-4 py-3 text-sm text-[#E5E0D8] placeholder-[#3A3A3A] focus:outline-none focus:border-[#D4A84B]/50 focus:ring-1 focus:ring-[#D4A84B]/20 transition-all"
                  />
                </div>

                {error && (
                  <p className="text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={loading || !email}
                  className="w-full bg-[#D4A84B] hover:bg-[#C49A35] disabled:opacity-40 disabled:cursor-not-allowed text-[#0A0A0A] font-semibold text-sm rounded-lg py-3 transition-all duration-200 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <svg
                        className="animate-spin w-4 h-4"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="3"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Sending…
                    </>
                  ) : (
                    "Send magic link"
                  )}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-xs text-[#444] mt-6">
          By signing in you agree to our{" "}
          <span className="text-[#666] cursor-pointer hover:text-[#D4A84B] transition-colors">
            Terms of Service
          </span>
        </p>
      </div>
    </div>
  );
}
