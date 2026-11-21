import path from "node:path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
      // il motore dello scontorno (onnx, ~23 MB) non va in cache all'installazione: si scarica solo quando serve
      injectManifest: { globPatterns: ["**/*.{js,css,html,png,svg,woff2}"], globIgnores: ["**/ort*"] },
      manifest: {
        name: "Style.me",
        short_name: "Style.me",
        description: "Guardaroba, valigie e stile",
        lang: "it",
        theme_color: "#1E2840",
        background_color: "#FAF9F6",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: { proxy: { "/api": "http://localhost:8000" } },
  preview: { proxy: { "/api": "http://localhost:8000" } },
});
