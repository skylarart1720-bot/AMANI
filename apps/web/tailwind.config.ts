import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        amani: {
          yellow: '#FFED00',
          black: '#111111',
          white: '#FFFFFF',
          gray: '#EDEDED',
          darkgray: '#555555',
        },
      },
    },
  },
  plugins: [],
};

export default config;
