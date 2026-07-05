import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0D1B2A",
        accent: "#2E86C1",
        clean: "#1E8449",
        medium: "#E67E22",
        danger: "#C0392B",
        surface: "#F5F7FA",
      },
    },
  },
  plugins: [],
};

export default config;
