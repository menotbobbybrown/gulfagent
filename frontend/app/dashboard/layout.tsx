import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { DashboardShell } from "./DashboardShell";
import { ErrorBoundary } from "../components/ErrorBoundary";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return (
    <ErrorBoundary>
      <DashboardShell user={user}>{children}</DashboardShell>
    </ErrorBoundary>
  );
}
