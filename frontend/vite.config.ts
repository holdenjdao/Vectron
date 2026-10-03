import { defineConfig, loadEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";

/** Default backend address; override with VECTRON_API_URL (environment or .env file). */
const DEFAULT_BACKEND = "http://127.0.0.1:8000";

type Headers = Record<string, string | string[] | undefined>;

/**
 * The two proxy events we hook, typed structurally so this file type-checks
 * without @types/node (Vite's own typing of the emitter needs Node's types).
 */
interface ProxyEvents {
  on(
    event: "proxyReq",
    listener: (proxyReq: { setHeader(name: string, value: string): void }, req: { headers: Headers }) => void,
  ): unknown;
  on(event: "proxyRes", listener: (proxyRes: { headers: Headers }) => void): unknown;
}

const isEventStream = (value: string | string[] | undefined): boolean =>
  String(value ?? "").includes("text/event-stream");

/**
 * `/api` → FastAPI backend. Job event streams (SSE) must reach the browser
 * unbuffered: the proxy already pipes response chunks through as they arrive
 * (and aborts the upstream request when the browser disconnects), so we only
 * make sure nothing upstream compresses the stream (gzip buffers whole blocks)
 * and tell any intermediary not to buffer or transform it.
 */
const apiProxy = (target: string): ProxyOptions => ({
  target,
  changeOrigin: true,
  configure(proxy) {
    const events = proxy as unknown as ProxyEvents;
    events.on("proxyReq", (proxyReq, req) => {
      if (isEventStream(req.headers["accept"])) proxyReq.setHeader("accept-encoding", "identity");
    });
    events.on("proxyRes", (proxyRes) => {
      if (!isEventStream(proxyRes.headers["content-type"])) return;
      proxyRes.headers["cache-control"] = "no-cache, no-transform";
      proxyRes.headers["x-accel-buffering"] = "no";
      delete proxyRes.headers["content-length"];
    });
  },
});

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VECTRON_");
  const backend = env["VECTRON_API_URL"] || DEFAULT_BACKEND;
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: { "/api": apiProxy(backend) },
    },
    preview: {
      port: 4173,
      proxy: { "/api": apiProxy(backend) },
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
      // Mermaid is lazy-loaded and ships a few large diagram chunks; none load on the catalog.
      chunkSizeWarningLimit: 1600,
      // Two pages: the landing page at / and the factory app at /app/.
      rollupOptions: { input: { landing: "index.html", app: "app/index.html" } },
    },
  };
});
