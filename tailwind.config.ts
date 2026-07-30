import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0F172B",
        "ink-soft": "#1C2942",
        body: "#46536B",
        paper: "#EBEEF4",
        "paper-warm": "#F5F6FA",
        line: "#D5DAE5",
        amber: "#C4792E",
        "amber-ink": "#A05A1E",
        "amber-soft": "#E6C49C",
        steel: "#5D8CB9",
        sage: "#5F8AA0",
      },
      fontFamily: {
        serif: ["var(--font-instrument-serif)", "Georgia", "serif"],
        sans: ["var(--font-ibm-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-ibm-plex-mono)", "monospace"],
      },
      fontSize: {
        h1: "clamp(2.45rem, 5.2vw, 4.05rem)",
        h2: "clamp(1.95rem, 3.6vw, 2.85rem)",
      },
      maxWidth: {
        content: "1120px",
        reading: "680px",
      },
    },
  },
  plugins: [],
};

export default config;
