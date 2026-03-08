import type { Config } from 'tailwindcss';
const config: Config = {
  darkMode: 'class',
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: { extend: { colors: { primary: '#3b82f6', secondary: '#1e293b' } } },
  plugins: [],
};
export default config;
