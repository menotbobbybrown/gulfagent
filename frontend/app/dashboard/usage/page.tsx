"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";

interface UsageData {
  year_month: string;
  credits_used: number;
  credits_limit: number;
  credits_remaining: number;
  tasks_run: number;
  task_limit: number;
  automations_active: number;
  automation_limit: number;
  tier: string;
  subscription_status: string;
  percentage_used: number;
}

export default function UsagePage() {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  const getToken = useCallback(async () => {
    const { data: { session } } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  }, []);

  const fetchUsage = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch("/api/usage", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const { data } = await res.json();
        setUsage(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  const handleUpgrade = async (tier: "basic" | "pro") => {
    setCheckoutLoading(true);
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tier }),
      });
      if (res.ok) {
        const { data } = await res.json();
        if (data?.url) {
          window.location.href = data.url;
        }
      } else {
        const body = await res.json();
        console.error("Checkout failed:", body.error);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setCheckoutLoading(false);
      setShowUpgradeModal(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex justify-center py-20">
          <div className="w-6 h-6 border-2 border-[#D4A84B]/20 border-t-[#D4A84B] rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!usage) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="text-center py-20 border border-dashed border-[#181818] rounded-xl">
          <p className="text-[#666]">Could not load usage data.</p>
        </div>
      </div>
    );
  }

  const pctUsed = usage.percentage_used;
  const isLow = pctUsed >= 80;
  const isCritical = pctUsed >= 95;
  const barColor = isCritical ? "#EF4444" : isLow ? "#F59E0B" : "#D4A84B";

  const autoPct = usage.automation_limit
    ? Math.min(100, (usage.automations_active / usage.automation_limit) * 100)
    : 0;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-[#E5E0D8] tracking-tight">
          Usage & Billing
        </h1>
        <p className="text-sm text-[#555] mt-1">
          Track your monthly usage. Upgrade for more credits and features.
        </p>
      </div>

      {/* Plan info */}
      <div className="bg-[#0D0D0D] border border-[#181818] rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[10px] text-[#555] uppercase tracking-wider font-medium">Current Plan</span>
            <p className="text-lg font-semibold text-[#E5E0D8] mt-1 capitalize">{usage.tier}</p>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-[#555] uppercase tracking-wider font-medium">Status</span>
            <p className={`text-sm font-medium mt-1 ${
              usage.subscription_status === "active" ? "text-green-500" : "text-[#888]"
            }`}>
              {usage.subscription_status === "active"
                ? "✅ Active"
                : usage.subscription_status === "trial"
                ? "🆓 Trial"
                : "❌ " + usage.subscription_status}
            </p>
          </div>
        </div>
        {usage.tier !== "pro" && usage.tier !== "enterprise" && (
          <button
            onClick={() => setShowUpgradeModal(true)}
            className="mt-4 w-full px-4 py-2.5 bg-[#D4A84B] text-black text-sm font-medium rounded-lg hover:bg-[#C59B3F] transition-colors"
          >
            Upgrade to Pro
          </button>
        )}
      </div>

      {/* Credits progress */}
      <div className="bg-[#0D0D0D] border border-[#181818] rounded-xl p-5 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-[#E5E0D8]">Credits</h2>
          <span className="text-xs text-[#888]">
            {usage.credits_used.toLocaleString()} / {usage.credits_limit.toLocaleString()}
          </span>
        </div>
        <div className="w-full h-3 bg-[#1A1A1A] rounded-full overflow-hidden border border-[#242424]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pctUsed}%`, backgroundColor: barColor }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-[#555]">
          <span>{usage.credits_remaining.toLocaleString()} remaining</span>
          <span>{pctUsed}% used</span>
        </div>
      </div>

      {/* Tasks progress */}
      <div className="bg-[#0D0D0D] border border-[#181818] rounded-xl p-5 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-[#E5E0D8]">Tasks This Month</h2>
          <span className="text-xs text-[#888]">
            {usage.tasks_run.toLocaleString()} / {usage.task_limit.toLocaleString()}
          </span>
        </div>
        <div className="w-full h-3 bg-[#1A1A1A] rounded-full overflow-hidden border border-[#242424]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${usage.task_limit ? Math.min(100, (usage.tasks_run / usage.task_limit) * 100) : 0}%`,
              backgroundColor: "#D4A84B",
            }}
          />
        </div>
      </div>

      {/* Automations progress */}
      <div className="bg-[#0D0D0D] border border-[#181818] rounded-xl p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-[#E5E0D8]">Active Automations</h2>
          <span className="text-xs text-[#888]">
            {usage.automations_active} / {usage.automation_limit === 999999 ? "∞" : usage.automation_limit}
          </span>
        </div>
        {usage.automation_limit < 999999 && (
          <div className="w-full h-3 bg-[#1A1A1A] rounded-full overflow-hidden border border-[#242424]">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${autoPct}%`, backgroundColor: "#D4A84B" }}
            />
          </div>
        )}
        {usage.automation_limit === 999999 && (
          <p className="text-xs text-[#555]">Unlimited automations on your plan.</p>
        )}
      </div>

      {/* Upgrade Modal */}
      {showUpgradeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80">
          <div className="bg-[#0D0D0D] border border-[#181818] rounded-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-5 border-b border-[#181818] flex justify-between items-center">
              <h2 className="font-display text-lg font-semibold text-[#E5E0D8]">Upgrade Plan</h2>
              <button onClick={() => setShowUpgradeModal(false)} className="text-[#555] hover:text-[#888]">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              {/* Basic plan */}
              <div className="bg-[#0A0A0A] border border-[#1E1E1E] rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-display text-base font-semibold text-[#E5E0D8]">Basic</h3>
                    <p className="text-xs text-[#555]">Starting plan</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-[#E5E0D8]">AED 150</p>
                    <p className="text-[10px] text-[#555]">/month</p>
                  </div>
                </div>
                <ul className="space-y-1.5 text-xs text-[#888] mb-4">
                  <li>✓ 5,000 credits / month</li>
                  <li>✓ 50 tasks / month</li>
                  <li>✓ 5 automations</li>
                  <li>✓ WhatsApp integration</li>
                </ul>
                {usage.tier === "basic" ? (
                  <span className="block text-center text-xs text-[#555] py-2">Current plan</span>
                ) : (
                  <button
                    onClick={() => handleUpgrade("basic")}
                    disabled={checkoutLoading}
                    className="w-full px-4 py-2 bg-[#1A1A1A] text-[#888] text-sm font-medium rounded-lg hover:bg-[#222] transition-colors disabled:opacity-40"
                  >
                    {checkoutLoading ? "Loading…" : "Downgrade to Basic"}
                  </button>
                )}
              </div>

              {/* Pro plan */}
              <div className="bg-[#0A0A0A] border border-[#D4A84B]/30 rounded-xl p-5 relative">
                <span className="absolute -top-2.5 right-4 px-2 py-0.5 bg-[#D4A84B] text-black text-[10px] font-semibold rounded-full">
                  RECOMMENDED
                </span>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-display text-base font-semibold text-[#E5E0D8]">Pro</h3>
                    <p className="text-xs text-[#555]">Best for power users</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-[#E5E0D8]">AED 500</p>
                    <p className="text-[10px] text-[#555]">/month</p>
                  </div>
                </div>
                <ul className="space-y-1.5 text-xs text-[#888] mb-4">
                  <li>✓ 20,000 credits / month</li>
                  <li>✓ 200 tasks / month</li>
                  <li>✓ Unlimited automations</li>
                  <li>✓ WhatsApp integration</li>
                  <li>✓ API access</li>
                  <li>✓ Priority support</li>
                </ul>
                {usage.tier === "pro" ? (
                  <span className="block text-center text-xs text-[#555] py-2">Current plan</span>
                ) : (
                  <button
                    onClick={() => handleUpgrade("pro")}
                    disabled={checkoutLoading}
                    className="w-full px-4 py-2 bg-[#D4A84B] text-black text-sm font-semibold rounded-lg hover:bg-[#C59B3F] transition-colors disabled:opacity-40"
                  >
                    {checkoutLoading ? "Loading…" : "Upgrade to Pro"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}