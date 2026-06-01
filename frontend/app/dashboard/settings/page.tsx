"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Profile {
  id: string;
  email: string;
  phone: string | null;
  full_name: string | null;
  subscription_tier: string;
  subscription_status: string;
  preferred_language: string;
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [phone, setPhone] = useState("");
  const [phoneSaving, setPhoneSaving] = useState(false);
  const [phoneMsg, setPhoneMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
  }, []);

  async function getToken() {
    const { data: { session } } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  }

  async function fetchProfile() {
    const token = await getToken();
    if (!token) return;
    try {
      const res = await fetch("/api/users/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const { data } = await res.json();
        setProfile(data);
        setPhone(data.phone?.replace("+", "") ?? "");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSavePhone(e: React.FormEvent) {
    e.preventDefault();
    setPhoneSaving(true);
    setPhoneMsg(null);
    const token = await getToken();
    if (!token) return;
    try {
      const res = await fetch("/api/users/me/phone", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ phone }),
      });
      const body = await res.json();
      if (res.ok) {
        setProfile(body.data);
        setPhoneMsg({ type: "ok", text: "Phone number saved. You can now submit tasks via WhatsApp." });
      } else {
        setPhoneMsg({ type: "err", text: body?.detail ?? "Failed to save phone number." });
      }
    } catch {
      setPhoneMsg({ type: "err", text: "Network error." });
    } finally {
      setPhoneSaving(false);
    }
  }

  async function handleSignOut() {
    await createClient().auth.signOut();
    window.location.href = "/login";
  }

  async function handleLanguage(lang: "en" | "ar") {
    const token = await getToken();
    if (!token) return;
    await fetch(`/api/users/me/language?language=${lang}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    });
    setProfile((p) => p ? { ...p, preferred_language: lang } : p);
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 space-y-4">
        <div className="skeleton h-8 w-32 rounded-lg" />
        <div className="skeleton h-48 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="font-display text-2xl font-semibold text-[#E5E0D8] mb-6">Settings</h1>

      <div className="space-y-3">
        {/* Account */}
        <div className="bg-[#111111] border border-[#242424] rounded-2xl divide-y divide-[#1A1A1A]">
          <div className="p-5">
            <h2 className="text-xs font-medium text-[#555] uppercase tracking-wide mb-3">Account</h2>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#D4A84B]/10 border border-[#D4A84B]/20 flex items-center justify-center text-sm font-semibold text-[#D4A84B]">
                {profile?.email?.slice(0, 2).toUpperCase() ?? "??"}
              </div>
              <div>
                <p className="text-sm text-[#E5E0D8]">{profile?.email}</p>
                <p className="text-xs text-[#555]">
                  <span className="capitalize">{profile?.subscription_tier}</span> plan ·{" "}
                  <span className="capitalize">{profile?.subscription_status}</span>
                </p>
              </div>
            </div>
          </div>

          {/* WhatsApp phone link — T39 */}
          <div className="p-5">
            <h2 className="text-xs font-medium text-[#555] uppercase tracking-wide mb-1">
              WhatsApp Number
            </h2>
            <p className="text-xs text-[#444] mb-3">
              Link your number to submit tasks and receive results via WhatsApp.
            </p>
            <form onSubmit={handleSavePhone} className="flex gap-2">
              <div className="flex-1 flex items-center bg-[#0A0A0A] border border-[#2A2A2A] rounded-lg overflow-hidden focus-within:border-[#D4A84B]/40 transition-colors">
                <span className="text-sm text-[#444] px-3 border-r border-[#2A2A2A]">+</span>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
                  placeholder="971501234567"
                  className="flex-1 bg-transparent text-sm text-[#E5E0D8] px-3 py-2.5 outline-none placeholder-[#333]"
                />
              </div>
              <button
                type="submit"
                disabled={phoneSaving || !phone}
                className="bg-[#D4A84B] hover:bg-[#C49A35] disabled:opacity-30 text-[#0A0A0A] text-sm font-semibold rounded-lg px-4 transition-all"
              >
                {phoneSaving ? "Saving…" : "Save"}
              </button>
            </form>
            {phoneMsg && (
              <p className={`text-xs mt-2 ${phoneMsg.type === "ok" ? "text-[#10B981]" : "text-red-400"}`}>
                {phoneMsg.text}
              </p>
            )}
          </div>

          {/* Language preference */}
          <div className="p-5">
            <h2 className="text-xs font-medium text-[#555] uppercase tracking-wide mb-1">Language</h2>
            <p className="text-xs text-[#444] mb-3">
              Select your preferred language for WhatsApp communications and AI responses.
              <br />
              <span className="text-[#D4A84B]/80 italic">Arabic is recommended for Gulf-based tasks.</span>
            </p>
            <div className="flex gap-2">
              {(["en", "ar"] as const).map((lang) => (
                <button
                  key={lang}
                  onClick={() => handleLanguage(lang)}
                  className={`px-4 py-2 rounded-lg text-sm border transition-all ${
                    profile?.preferred_language === lang
                      ? "bg-[#D4A84B]/10 border-[#D4A84B]/30 text-[#D4A84B]"
                      : "bg-[#0A0A0A] border-[#2A2A2A] text-[#666] hover:text-[#888]"
                  }`}
                >
                  {lang === "en" ? "English" : "العربية (Arabic)"}
                </button>
              ))}
            </div>
          </div>

        </div>

        {/* Session */}
        <div className="bg-[#111111] border border-[#242424] rounded-2xl p-5">
          <h2 className="text-xs font-medium text-[#555] uppercase tracking-wide mb-3">Session</h2>
          <button
            onClick={handleSignOut}
            className="text-sm text-red-400 hover:text-red-300 border border-red-400/20 hover:border-red-400/40 rounded-lg px-4 py-2 transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
