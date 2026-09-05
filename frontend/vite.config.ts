import { sites } from '@openai/sites-vite-plugin';
import tailwindcss from '@tailwindcss/postcss';
import vinext from 'vinext';
import { defineConfig } from 'vite';
export default defineConfig({
  css: { postcss: { plugins: [tailwindcss()] } },
  server: { port: 3001, proxy: { '/api': 'http://127.0.0.1:8000' } },
  plugins: [vinext(), sites()],
});
