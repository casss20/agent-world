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
      },
      backdropBlur: {
        xs:  '4px',
        sm:  '8px',
        md:  '12px',
        lg:  '20px',
        xl:  '32px',
      },
      boxShadow: {
        'glass':      '0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.07)',
        'glass-cyan': '0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(0,243,255,0.12), 0 0 0 1px rgba(0,243,255,0.15)',
        'glow-cyan':  '0 0 20px rgba(0,243,255,0.35)',
        'glow-pink':  '0 0 20px rgba(255,0,110,0.35)',
      },
    },
  },
  plugins: [],
}
