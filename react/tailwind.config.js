/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // VSCode-like dark theme
        'vscode': {
          'bg': '#1e1e1e',
          'bg-light': '#252526',
          'bg-lighter': '#2d2d2d',
          'bg-hover': '#3c3c3c',
          'bg-active': '#505050',
          'border': '#404040',
          'text': '#cccccc',
          'text-dim': '#858585',
          'accent': '#007acc',
          'green': '#4ec9b0',
          'yellow': '#dcdcaa',
          'red': '#f14c4c',
          'blue': '#569cd6',
          'purple': '#c586c0',
        },
        // Agent status colors
        'agent': {
          'idle': '#4ec9b0',
          'working': '#dcdcaa',
          'error': '#f14c4c',
        }
      },
      fontFamily: {
        'mono': ['Consolas', 'Monaco', 'Courier New', 'monospace'],
        'sans': ['Segoe UI', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'xs': ['11px', '16px'],
        'sm': ['12px', '18px'],
        'base': ['13px', '20px'],
        'lg': ['14px', '22px'],
        'xl': ['16px', '24px'],
      },
    },
  },
  plugins: [],
}