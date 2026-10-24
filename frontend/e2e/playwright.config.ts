/**
 * Dashboard golden path (PLAN T42, SRS §27.7) against a running stack: `docker compose up --build -d`, then
 * `make test-e2e` (which writes the fixture CSV and runs this). Uses the installed Chrome.
 *
 *   E2E_BASE_URL   dashboard URL (default http://localhost:8080)
 *   E2E_USERNAME   an ADMIN account (default: the bootstrap admin name)
 *   E2E_PASSWORD   its password (required)
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  timeout: 12 * 60_000,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    channel: "chrome",
    headless: true,
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    actionTimeout: 30_000,
    screenshot: "only-on-failure",
  },
});
