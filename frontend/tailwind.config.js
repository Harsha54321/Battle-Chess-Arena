/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    extend: {
      colors: {
        gaming: {
          dark: "#020617",
          darker: "#01040f",
          card: "rgba(15, 23, 42, 0.7)",
          cyan: "#00d4ff",
          gold: "#ffd700",
        },
      },

      boxShadow: {
        cyanGlow: "0 0 25px rgba(0, 212, 255, 0.5)",
        goldGlow: "0 0 25px rgba(255, 215, 0, 0.5)",
      },

      backdropBlur: {
        xs: "2px",
      },

      fontFamily: {
        sans: ["Orbitron", "sans-serif"],
        gaming: ["Orbitron", "sans-serif"],
      },
    },
  },

  plugins: [],
};