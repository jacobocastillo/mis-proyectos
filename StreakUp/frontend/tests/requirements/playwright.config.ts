import { defineConfig } from "@playwright/test";
import baseConfig from "../../playwright.config";

export default defineConfig({
  ...baseConfig,
  testDir: ".",
  testMatch: ["rnf/*.spec.ts"],
  fullyParallel: false,
  workers: 1,
});
