/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: '#E9EBE7',
          2: '#DCDFD9',
        },
        surface: {
          DEFAULT: '#F3F4F1',
          2: '#E6E9E3',
        },
        ink: {
          DEFAULT: '#172820',
          2: '#172820',
        },
        brand: {
          DEFAULT: '#172820',
        },
        text: {
          DEFAULT: '#1C2C23',
          2: '#58665C',
        },
        line: '#C5CBC3',
        accent: {
          DEFAULT: '#172820',
          2: '#C29A5B', // antique brass
          hover: '#172820',
        },
        status: {
          ok: '#172820',
          approved: '#172820',
          'approved-bg': '#E6E9E3',
          warn: '#896421',
          'warn-bg': '#F0E5CD',
          err: '#A8433A',
          rec: '#C7473B',
          'rec-bg': '#F1DFDB',
          ai: '#5A7183',
          'ai-bg': '#E0E6E8',
        },
      },
      fontFamily: {
        serif: ['Bricolage Grotesque', 'Segoe UI', 'system-ui', 'sans-serif'],
        sans: ['Figtree', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        hand: ['Caveat', 'cursive'],
        deva: ['Noto Sans Devanagari', 'Nirmala UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
