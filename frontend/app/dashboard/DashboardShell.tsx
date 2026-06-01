"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { UsageBar } from "../components/UsageBar";
import { ApprovalModal } from "../components/ApprovalModal";
import type { User } from "@supabase/supabase-js";

interface PendingApproval {
  id: string;
  task_id: string;
  action_type: string;
  action_payload: Record<string, unknown>;
  expires_at: string;
}

const NAV_ITEMS = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
        <rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
        <rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
        <rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    ),
  },
  {
    href: "/dashboard/tasks",
    label: "Tasks",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M3 4h10M3 8h8M3 12h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: "/dashboard/automations",
    label: "Automations",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.3" />
        <path d="M8 5v3l2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: "/dashboard/skills",
    label: "Skills",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 1l1.8 4H14l-3.7 2.7 1.4 4.3L8 9.4l-3.7 2.6 1.4-4.3L2 5h4.2L8 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    href: "/dashboard/settings",
    label: "Settings",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.3" />
        <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.42 1.42M11.53 11.53l1.42 1.42M3.05 12.95l1.42-1.42M11.53 4.47l1.42-1.42" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
    ),
  },
];

interface DashboardShellProps {
  user: User;
  children: React.ReactNode;
}

interface UsageData {
  credits_used: number;
  credits_limit: number;
  tier: string;
}

export function DashboardShell({ user, children }: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [usage, setUsage] = useState<UsageData>({ credits_used: 0, credits_limit: 5000, tier: "basic" });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);

  const getToken = useCallback(async () => {
    const { data: { session } } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  }, []);

  // Fetch usage summary
  useEffect(() => {
    async function fetchUsage() {
      try {
        const token = await getToken();
        if (!token) return;
        const res = await fetch("/api/usage", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const { data } = await res.json();
          setUsage({ credits_used: data.credits_used, credits_limit: data.credits_limit, tier: data.tier });
        }
      } catch {}
    }
    fetchUsage();
  }, [getToken]);

  // T31 — Poll pending approvals every 5s
  useEffect(() => {
    async function fetchApprovals() {
      try {
        const token = await getToken();
        if (!token) return;
        const res = await fetch("/api/approvals/pending", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const { data } = await res.json();
          setPendingApprovals(data ?? []);
        }
      } catch {}
    }
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 5_000);
    return () => clearInterval(interval);
  }, [getToken]);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  const initials = user.email
    ? user.email.slice(0, 2).toUpperCase()
    : "GA";

  return (
    <div className="flex h-screen bg-[#0A0A0A] overflow-hidden">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative z-30 flex flex-col w-56 h-full bg-[#0D0D0D] border-r border-[#181818]
          transition-transform duration-200 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-[#181818]">
          <div className="w-7 h-7 rounded-lg bg-[#D4A84B]/10 border border-[#D4A84B]/20 flex items-center justify-center flex-shrink-0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L3 7v10l9 5 9-5V7L12 2z" stroke="#D4A84B" strokeWidth="1.5" strokeLinejoin="round" />
              <path d="M12 2v20M3 7l9 5 9-5" stroke="#D4A84B" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
          </div>
          <span className="font-display text-sm font-semibold text-[#E5E0D8] tracking-tight">
            GulfAgent
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all
                  ${isActive
                    ? "bg-[#D4A84B]/10 text-[#D4A84B] border border-[#D4A84B]/10"
                    : "text-[#666] hover:text-[#C8C0B4] hover:bg-[#141414]"
                  }
                `}
              >
                <span className={isActive ? "text-[#D4A84B]" : ""}>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="px-3 py-4 border-t border-[#181818]">
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#141414] transition-colors group cursor-default">
            <div className="w-7 h-7 rounded-lg bg-[#D4A84B]/20 flex items-center justify-center text-xs font-semibold text-[#D4A84B] flex-shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-[#888] truncate">{user.email}</p>
              <p className="text-[10px] text-[#444] capitalize">{usage.tier}</p>
            </div>
            <button
              onClick={handleSignOut}
              title="Sign out"
              className="opacity-0 group-hover:opacity-100 transition-opacity text-[#444] hover:text-[#888]"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M5 2H3a1 1 0 00-1 1v8a1 1 0 001 1h2M9 10l3-3-3-3M12 7H5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-[#181818] bg-[#0A0A0A] flex-shrink-0">
          <button
            className="lg:hidden text-[#555] hover:text-[#888] transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>

          <div className="flex-1" />

          {/* Approval badge */}
          {pendingApprovals.length > 0 && (
            <div className="flex items-center gap-1.5 mr-3">
              <span className="w-2 h-2 rounded-full bg-[#F59E0B] animate-pulse" />
              <span className="text-xs text-[#F59E0B] font-medium">
                {pendingApprovals.length} approval{pendingApprovals.length > 1 ? "s" : ""}
              </span>
            </div>
          )}

          <UsageBar
            creditsUsed={usage.credits_used}
            creditsLimit={usage.credits_limit}
            tier={usage.tier}
          />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* T31 — Approval modal: show first pending approval */}
      {pendingApprovals[0] && (
        <ApprovalModal
          approval={pendingApprovals[0]}
          onClose={() => setPendingApprovals((prev) => prev.slice(1))}
          onDecision={(id, _decision) =>
            setPendingApprovals((prev) => prev.filter((a) => a.id !== id))
          }
        />
      )}
    </div>
  );
}
