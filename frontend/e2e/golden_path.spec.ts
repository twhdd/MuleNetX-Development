/**
 * AT-E2E-01 through the dashboard: upload → pipeline READY → account risk with SHAP → case with a finding →
 * ring → hypothetical RANK simulation → evaluation run → copilot. Every step uses the real API; the copilot
 * step accepts an answer or the explicit unavailable state (Ollama is optional, SRS §21.7).
 */
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const USERNAME = process.env.E2E_USERNAME ?? "admin";
const PASSWORD = process.env.E2E_PASSWORD ?? "";
const CSV = path.resolve(import.meta.dirname, ".data/golden.csv");

/** In-app navigation: the session lives in tab memory only (SRS §20.2), so a page load would sign out. */
async function go(page: Page, to: string) {
  await page.evaluate((x) => {
    window.history.pushState({}, "", x);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, to);
}

async function signIn(page: Page) {
  await page.goto("/login");
  await page.fill("input[autocomplete=username]", USERNAME);
  await page.fill("input[type=password]", PASSWORD);
  await page.click("button[type=submit]");
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 30_000 });
}

test("golden path through the dashboard", async ({ page }) => {
  expect(PASSWORD, "set E2E_PASSWORD to the ADMIN account's password").not.toBe("");
  await signIn(page);

  // upload a new dataset version and follow its pipeline run to READY
  await go(page, "/admin/ingestion");
  await page.setInputFiles("input[type=file]", CSV);
  await page.getByLabel("Dataset name").fill("e2e golden path");
  await page.getByLabel("Version").fill(`v${Date.now()}`);
  await page.getByRole("button", { name: "Upload and start pipeline" }).click();
  const runHref = await page.getByRole("link", { name: /^Open run / }).getAttribute("href");
  expect(runHref).toMatch(/^\/admin\/pipelines\//);
  await expect(async () => {
    await go(page, "/admin/ingestion");
    await go(page, runHref!);
    await expect(page.getByText("Ready", { exact: true }).first()).toBeVisible({ timeout: 3_000 });
  }).toPass({ timeout: 10 * 60_000, intervals: [5_000] });

  // triage selects the top-scored account; its SHAP is the ML component only; then its workspace
  await go(page, "/");
  const shapNote = /This explanation covers the ML component \(ml_score\) only/;
  await expect(page.getByText(shapNote).first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "Open workspace" }).click();
  await page.waitForURL(/\/accounts\//);
  await expect(page.getByText(shapNote).first()).toBeVisible({ timeout: 60_000 });

  // copilot on this account: an AI INTERPRETATION answer, or the explicit unavailable state
  await page.getByRole("tab", { name: "Copilot" }).click();
  const copilot = page.getByRole("region", { name: "Copilot" });
  await copilot.getByRole("button", { name: "Why is this account scored this way?" }).click();
  await expect(copilot.locator("[data-intent], [data-code]")).toBeVisible({ timeout: 60_000 });
  await expect(copilot.getByText("AI INTERPRETATION").first()).toBeVisible();

  // open a case for the account and record a finding
  await page.getByRole("button", { name: "Open case" }).click();
  await page.waitForURL(/\/cases\//);
  const findingForm = page.getByRole("form", { name: "Record a finding" });
  await findingForm.getByPlaceholder("What you observed and why it matters").fill("Inflow is forwarded within the hour.");
  await findingForm.getByRole("button", { name: "Record finding" }).click();
  await expect(page.getByText("Inflow is forwarded within the hour.").first()).toBeVisible();

  // rings → a potential fraud ring candidate → hypothetical RANK simulation
  await go(page, "/rings?class=POTENTIAL_FRAUD_RING_CANDIDATE");
  await page.locator("tbody tr[data-clickable]").first().click();
  await page.getByRole("link", { name: "Simulate disruption" }).click();
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByText("Hypothetical change").first()).toBeVisible({ timeout: 5 * 60_000 });
  await expect(page.getByText("HYPOTHETICAL SIMULATION").first()).toBeVisible();

  // evaluation run over the model's test split
  await go(page, "/evaluation");
  await page.getByRole("button", { name: "Run evaluation" }).click();
  await expect(async () => {
    await expect(page.getByLabel("Progression")).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 5 * 60_000, intervals: [5_000] });
});
