"use client";

import Link from "next/link";

export default function BillingCancelPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-center">
      <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-[#F59E0B]/10 border border-[#F59E0B]/20 flex items-center justify-center">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
        </svg>
      </div>
      <h1 className="font-display text-xl font-semibold text-[#E5E0D8] mb-2">
        Checkout Cancelled
      </h1>
      <p className="text-sm text-[#555] mb-6">
        No changes were made. You can upgrade anytime from your usage page.
      </p>
      <div className="flex gap-3 justify-center">
        <Link
          href="/dashboard/usage"
          className="px-6 py-2.5 bg-[#D4A84B] text-black text-sm font-medium rounded-lg hover:bg-[#C59B3F] transition-colors"
        >
          View Plans
        </Link>
        <Link
          href="/dashboard"
          className="px-6 py-2.5 bg-[#1A1A1A] text-[#888] text-sm font-medium rounded-lg hover:bg-[#222] transition-colors border border-[#2A2A2A]"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}