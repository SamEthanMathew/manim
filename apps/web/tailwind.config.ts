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
        // 3b1b-ish accent palette
        accent: {
          blue: "#3498DB",
          yellow: "#FFFF00",
          red: "#E74C3C",
          green: "#2ECC71",
          ink: "#0B0E14",
        },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo"],
      },
    },
  },
  plugins: [],
};

export default config;
