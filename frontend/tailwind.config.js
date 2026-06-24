/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: { light: "#f8fafc", dark: "#0f172a" },
        card: { light: "#ffffff", dark: "#1e293b" },
      },
    },
  },
  plugins: [],
};
