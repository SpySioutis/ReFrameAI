/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0b0d10",
          900: "#101318",
          850: "#151a21",
          800: "#1b212a",
          700: "#262e3a",
          600: "#39434f",
        },
        accent: {
          400: "#7aa5ff",
          500: "#5b8cff",
          600: "#3f6fe0",
        },
      },
    },
  },
  plugins: [],
};
