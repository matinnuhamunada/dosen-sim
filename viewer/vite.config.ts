import { createReadStream, existsSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";

// Dev convenience: serve the repository's runs/ folder at /runs so a log can be opened
// with ?run=/runs/<name>/events.jsonl. The built viewer is static and uses a file picker.
function serveRuns(): Plugin {
  const root = resolve(__dirname, "..", "runs");
  return {
    name: "lecsim-serve-runs",
    configureServer(server) {
      server.middlewares.use("/runs", (req, res, next) => {
        const file = resolve(root, "." + decodeURIComponent((req.url ?? "").split("?")[0]));
        if (!file.startsWith(root) || !existsSync(file) || !statSync(file).isFile()) return next();
        res.setHeader("Content-Type", "text/plain; charset=utf-8");
        createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [serveRuns()],
  build: { chunkSizeWarningLimit: 900 }, // three.js is one ~700 kB chunk; fine for a static app
});
