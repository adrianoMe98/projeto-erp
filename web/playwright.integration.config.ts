import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  testMatch: "supabase.spec.ts",
  workers: 1,
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:3000/login",
    reuseExistingServer: false,
    timeout: 120000,
    env: { SUPABASE_TEST_SERVICE_KEY: "" },
  },
});
