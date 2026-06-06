import type { Metadata } from "next";
import "./globals.css";
import { RTLProvider } from "@/lib/rtl-provider";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "GulfAgent — AI Agent Platform for GCC",
  description: "Automate business tasks with AI. Built for UAE, Saudi Arabia, and the wider Gulf.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="noise antialiased">
        <RTLProvider>
          {children}
        </RTLProvider>
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: "#111",
              color: "#E5E0D8",
              border: "1px solid #242424",
              borderRadius: "12px",
              fontSize: "14px",
            },
            success: {
              iconTheme: { primary: "#10B981", secondary: "#0A0A0A" },
            },
            error: {
              iconTheme: { primary: "#EF4444", secondary: "#0A0A0A" },
            },
          }}
        />
      </body>
    </html>
  );
}

