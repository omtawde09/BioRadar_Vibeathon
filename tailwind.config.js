/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./bioradar/webapp_static/**/*.{html,js}"
  ],
  theme: {
    extend: {
      colors: {
        eco: {
          bg: "#fcfcf0",
          contrast: "#f8fef4",
          pink: "#bd3b67",
          "pink-hover": "#a63057",
          green: "#689660",
          "green-dark": "#1b5e20",
          "green-hover": "#588051",
          dark: "#020404",
          cream: "#fcfcf0",
          sage: "#f8fef4",
          border: "#e2e6d8",
          card: "#ffffff",
          muted: "#5a6258"
        }
      },
      fontFamily: {
        sans: ['"Poppins"', 'system-ui', '-apple-system', 'sans-serif'],
        body: ['"Poppins"', 'system-ui', '-apple-system', 'sans-serif'],
        heading: ['"Bungee"', 'cursive', 'sans-serif'],
        display: ['"Bungee"', 'cursive', 'sans-serif'],
      },
      boxShadow: {
        'eco-sm': '0 2px 8px rgba(2, 4, 4, 0.04)',
        'eco-md': '0 8px 24px -4px rgba(2, 4, 4, 0.08), 0 2px 6px -1px rgba(2, 4, 4, 0.04)',
        'eco-lg': '0 16px 36px -6px rgba(2, 4, 4, 0.12), 0 4px 12px -2px rgba(2, 4, 4, 0.06)',
        'eco-card-depth': '0 10px 30px -5px rgba(2, 4, 4, 0.08), 0 4px 12px -2px rgba(104, 150, 96, 0.12)',
        'eco-card-hover': '0 20px 40px -10px rgba(2, 4, 4, 0.14), 0 8px 20px -4px rgba(104, 150, 96, 0.18)',
        'eco-btn': '0 4px 14px 0 rgba(104, 150, 96, 0.39)',
        'eco-btn-pink': '0 4px 14px 0 rgba(189, 59, 103, 0.39)',
        'eco-halo': '0 0 32px rgba(104, 150, 96, 0.25)',
        'eco-halo-large': '0 0 48px rgba(104, 150, 96, 0.35)',
        'eco-pink-halo': '0 0 32px rgba(189, 59, 103, 0.22)',
      },
      borderRadius: {
        'eco-xl': '1.5rem',
        'eco-2xl': '2rem',
        'eco-3xl': '2.5rem',
      }
    },
  },
  plugins: [],
}
