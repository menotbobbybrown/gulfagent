"use client";

import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * T71 — React error boundary component.
 * Catches rendering errors and displays a fallback UI instead of crashing.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center px-4">
          <div className="max-w-md text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/20 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
              </svg>
            </div>
            <h1 className="font-display text-xl font-semibold text-[#E5E0D8] mb-2">
              Something went wrong
            </h1>
            <p className="text-sm text-[#666] mb-6">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="px-6 py-2.5 bg-[#D4A84B] text-black text-sm font-medium rounded-lg hover:bg-[#C59B3F] transition-colors"
            >
              Reload Page
            </button>
            {this.state.error && (
              <details className="mt-4">
                <summary className="text-[10px] text-[#444] cursor-pointer hover:text-[#666]">
                  Error details
                </summary>
                <pre className="mt-2 text-[10px] text-[#555] text-left bg-[#0D0D0D] border border-[#181818] rounded-lg p-3 overflow-auto max-h-32">
                  {this.state.error.message}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}