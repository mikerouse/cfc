/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./council_finance/templates/**/*.html",
    "./council_finance/static/**/*.js",
    "./static/**/*.js",
    "./frontend/**/*.html",
    "./frontend/src/**/*.jsx",
  ],
  safelist: [
    'bg-emerald-600',
    'bg-emerald-700',
    'hover:bg-emerald-700',
    'hover:bg-blue-700',
    'hover:bg-gray-300',
    'text-white',
    'order-1',
    'order-2',
    'xl:order-1',
    'xl:order-2',
    'xl:col-span-1',
    'xl:col-span-3',
    'xl:grid-cols-4',
    'grid-cols-1',
    'gap-6',
    'xl:gap-8',
    'xl:hidden',
    'xl:block'
  ],
  theme: {
    extend: {
      screens: {
        'desktop': '1280px',
      },
      maxWidth: {
        'desktop': '1280px',
      },
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe', 
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}