import { defineConfig } from "vite";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Separate from vite.config.js on purpose -- that file's `build.lib` /
// `define` block is tuned for the production IIFE bundle and isn't
// relevant to (and would just add noise to) the test run.
export default defineConfig({
  test: {
    environment: "node", // composables here don't touch the DOM; bump to "jsdom" if a future test needs it
    include: ["src/**/*.test.js"],
  },
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
});
