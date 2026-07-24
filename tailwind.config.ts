import type { Config } from "tailwindcss";

/**
 * Tokens de design — paleta sóbria/científica.
 * brand  = azul-profundo (autoridade, calma clínica)
 * accent = verde-petróleo (ação/CTA, sem "vermelho de lançamento")
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f6fa",
          100: "#dcebf3",
          200: "#bcd8e8",
          300: "#8dbcd6",
          400: "#579abd",
          500: "#357ea3",
          600: "#256689",
          700: "#1f5270",
          800: "#1e465d",
          900: "#0e3a5d",
          950: "#0a2740",
        },
        accent: {
          50: "#f0fdf9",
          100: "#ccfbef",
          500: "#14b8a6",
          600: "#0d9488",
          700: "#0f766e",
          800: "#115e59",
        },
        /** Dourado/âmbar sutil — reservado para destaques de credencial */
        gold: {
          100: "#fdf3d9",
          300: "#f0d78c",
          400: "#e2b64f",
          500: "#c99a2e",
          600: "#a67c1f",
        },
      },
      backgroundImage: {
        "hero-glow":
          "radial-gradient(60% 50% at 85% 20%, rgba(87,154,189,0.18) 0%, rgba(87,154,189,0) 100%), radial-gradient(45% 40% at 10% 85%, rgba(20,184,166,0.12) 0%, rgba(20,184,166,0) 100%)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      maxWidth: {
        content: "72rem",
      },
    },
  },
  plugins: [],
};

export default config;
