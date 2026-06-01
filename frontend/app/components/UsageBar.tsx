"use client";

interface UsageBarProps {
  creditsUsed: number;
  creditsLimit: number;
  tier: string;
}

export function UsageBar({ creditsUsed, creditsLimit, tier }: UsageBarProps) {
  const pct = Math.min(100, (creditsUsed / creditsLimit) * 100);
  const isLow = pct >= 80;
  const isCritical = pct >= 95;

  const barColor = isCritical
    ? "#EF4444"
    : isLow
    ? "#F59E0B"
    : "#D4A84B";

  return (
    <div className="flex items-center gap-3">
      <div className="hidden sm:flex flex-col items-end">
        <span className="text-[10px] text-[#555] uppercase tracking-wide font-medium">
          {tier}
        </span>
        <span className="text-xs text-[#888]">
          {creditsUsed.toLocaleString()}{" "}
          <span className="text-[#444]">/ {creditsLimit.toLocaleString()}</span>
        </span>
      </div>
      <div className="w-24 h-1.5 bg-[#1A1A1A] rounded-full overflow-hidden border border-[#242424]">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}
