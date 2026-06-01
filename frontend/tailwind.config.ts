import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core palette — desert night
        bg: {
          base: "#0A0A0A",
          surface: "#111111",
          elevated: "#1A1A1A",
          border: "#242424",
        },
        sand: {
          50: "#FDF8F0",
          100: "#F5E6C8",
          200: "#E8CA8A",
          300: "#D4A84B",
          400: "#C49A35",
          500: "#A07828",
        },
        accent: {
          DEFAULT: "#D4A84B",   // warm gold
          dim: "#7A5C1E",
          glow: "rgba(212,168,75,0.15)",
        },
        status: {
          pending: "#4B5563",
          running: "#3B82F6",
          completed: "#10B981",
          failed: "#EF4444",
          awaiting: "#F59E0B",
          cancelled: "#6B7280",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        mono: ["var(--font-mono)", "monospace"],
        body: ["var(--font-body)", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "spin-slow": "spin 3s linear infinite",
        shimmer: "shimmer 1.5s infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      backgroundImage: {
        "gold-shimmer":
          "linear-gradient(90deg, transparent 0%, rgba(212,168,75,0.1) 50%, transparent 100%)",
        "grid-subtle":
          "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;
