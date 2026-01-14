/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primaryRed: '#8B0000',      // Dark Crimson
        accentRed: '#DC143C',       // Crimson Red
        lightRed: '#C41E3A',        // Medium Crimson
        charcoalBlack: '#0F0F0F',   // Charcoal Black
        darkGray: '#1A1A1A',        // Dark Gray
        mediumGray: '#2A2A2A',      // Medium Gray
        lightGray: '#A0AEC0',       // Light Gray
        white: '#FFFFFF',           // Pure White
        offWhite: '#F5F5F5',        // Off-white
        agedGold: '#D4AF37',        // Aged Gold
        lightGold: '#C9A961',       // Lighter Aged Gold
      },
      fontFamily: {
        cinzel: ['Cinzel', 'serif'],
        roboto: ['Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}