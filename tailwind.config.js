/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        primary:        'var(--color-primary)',
        'primary-dark': 'var(--color-primary-dark)',
        'primary-light':'var(--color-primary-light)',
        secondary:      'var(--color-secondary)',
        accent:         'var(--color-accent)',
      },
      fontFamily: {
        sans: ['var(--font-main)'],
      },
    },
  },
  plugins: [],
}
