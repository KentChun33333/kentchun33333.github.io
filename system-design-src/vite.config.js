import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Built output is committed to ../system-design and served by GitHub Pages.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: '../system-design',
    emptyOutDir: true,
  },
});
