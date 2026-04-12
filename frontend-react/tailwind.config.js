/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gray: {
          950: '#0a0a0f',
          900: '#12121a',
          800: '#1e1e2e',
        },
        cyan: {
          400: '#00f3ff',
          500: '#00d4ff',
          600: '#00b8e6',
        }
      }
    },
  },
  plugins: [],
}
