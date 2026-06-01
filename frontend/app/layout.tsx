import type { Metadata } from "next";
import "./globals.css";
import { RTLProvider } from "@/lib/rtl-provider";

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
      </body>
    </html>
  );
}

