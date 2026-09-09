/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'vgu-orange': '#FF670D',
        'vgu-orange-dark': '#E55D0C',
        'vgu-orange-light': '#FF8A3B',
        'vgu-black': '#000000',
        'vgu-surface': '#1F1F1F',
        'vgu-text': '#EFEFEF',
        'vgu-muted': '#BDBDBD',
      },
      fontFamily: {
        sans: ['Poppins', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
