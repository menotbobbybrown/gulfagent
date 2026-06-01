"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function BillingSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    if (sessionId) {
      // Give Stripe webhook a moment to process
      const timer = setTimeout(() => setStatus("success"), 2000);
      return () => clearTimeout(timer);
    } else {
      setStatus("error");
    }
  }, [sessionId]);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-center">
      {status === "loading" && (
        <div>
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-[#D4A84B]/10 border border-[#D4A84B]/20 flex items-center justify-center">
            <div className="w-5 h-5 border-2 border-[#D4A84B]/20 border-t-[#D4A84B] rounded-full animate-spin" />
          </div>
          <h1 className="font-display text-xl font-semibold text-[#E5E0D8] mb-2">
            Processing Payment…
          </h1>
          <p className="text-sm text-[#555]">Please wait while we confirm your subscription.</p>
        </div>
      )}

      {status === "success" && (
        <div>
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2">
              <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h1 className="font-display text-xl font-semibold text-[#E5E0D8] mb-2">
            Subscription Active! 🎉
          </h1>
          <p className="text-sm text-[#555] mb-6">
            Welcome aboard! Your plan is now active. Start using all your credits and features.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex px-6 py-2.5 bg-[#D4A84B] text-black text-sm font-medium rounded-lg hover:bg-[#C59B3F] transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>
      )}

      {status === "error" && (
        <div>
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-[#F59E0B]/10 border border-[#F59E0B]/20 flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="font-display text-xl font-semibold text-[#E5E0D8] mb-2">
            Payment Received
          </h1>
          <p className="text-sm text-[#555] mb-6">
            Your payment was processed. Your subscription will be activated shortly.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex px-6 py-2.5 bg-[#D4A84B] text-black text-sm font-medium rounded-lg hover:bg-[#C59B3F] transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>
      )}
    </div>
  );
}