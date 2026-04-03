const path = require("path");

const auditRoot = path.join(__dirname, "ui-audit");

/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: path.join(auditRoot, "tests"),
  timeout: 120_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { outputFolder: path.join(auditRoot, "report", "html"), open: "never" }],
    ["json", { outputFile: path.join(auditRoot, "report", "results.json") }],
  ],
  outputDir: path.join(auditRoot, "report", "artifacts"),
  use: {
    baseURL: "http://127.0.0.1:5070",
    browserName: "chromium",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    viewport: {
      width: 1440,
      height: 1200,
    },
  },
  webServer: {
    command: "conda run -n canvas-bulk-panel python app.py",
    url: "http://127.0.0.1:5070",
    reuseExistingServer: true,
    env: {
      FLASK_HOST: "127.0.0.1",
      FLASK_PORT: "5070",
      FLASK_DEBUG: "0",
      CANVAS_PANEL_ENV_FILE: path.join(auditRoot, ".env.ui"),
      CANVAS_PANEL_DATA_DIR: path.join(auditRoot, "runtime-data"),
      ENABLE_LEGACY_JSON_IMPORT: "0",
    },
    timeout: 120_000,
  },
};
