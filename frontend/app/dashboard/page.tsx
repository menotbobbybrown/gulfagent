"use client";

import { useState } from "react";
import { TaskInput } from "../components/TaskInput";
import { TaskFeed } from "../components/TaskFeed";

export default function DashboardPage() {
  const [lastTaskId, setLastTaskId] = useState<string | null>(null);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Page heading */}
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-[#E5E0D8] tracking-tight">
          Command Center
        </h1>
        <p className="text-sm text-[#555] mt-1">
          Type a task and let the agent handle it.
        </p>
      </div>

      {/* Task input */}
      <div className="mb-8">
        <TaskInput onTaskCreated={(id) => setLastTaskId(id)} />
      </div>

      {/* Live task feed */}
      <TaskFeed newTaskId={lastTaskId} />
    </div>
  );
}
