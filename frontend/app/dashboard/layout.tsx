import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { DashboardShell } from "./DashboardShell";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch usage from API
  let usage = {
    credits_used: 0,
    credits_limit: 5000,
    tier: "basic",
    credits_remaining: 5000,
    tasks_run: 0,
  };
  try {
    // Usage is fetched client-side in DashboardShell to avoid server-side API auth complexity
  } catch {}

  return <DashboardShell user={user}>{children}</DashboardShell>;
}
