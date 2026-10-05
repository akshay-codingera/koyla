/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        coal: {
          pitch: '#0c0e12',
          dark: '#12151b',
          surface: '#181d24',
          card: '#202630',
        },
        graphite: {
          border: '#2c3543',
        },
        hairline: '#374151',
        paper: {
          light: '#f7f9fb',
          subtle: '#edf1f5',
          border: '#d2d8e0',
        },
        ore: {
          copper: '#9c5828',
          'copper-dark': '#7b431e',
        },
        industrial: {
          blue: '#1b365d',
          'blue-light': '#24487b',
        }
      }
    },
  },
  plugins: [],
}
