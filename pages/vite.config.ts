import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  base: process.env.PAGES_BASE || "/xiamimate-stock-lab/",
  plugins: [react()],
  build: { outDir: "../dist/pages", emptyOutDir: true },
  server: { host: "127.0.0.1", port: 5228, strictPort: true },
  preview: { host: "127.0.0.1", port: 5228, strictPort: true },
});
