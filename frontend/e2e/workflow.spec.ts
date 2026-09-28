import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

test("real saved River checkpoint drives the workflow, policy, comparison, and export", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByTestId("saved-days")).toHaveText("6days / request");
  await expect(page.getByTestId("current-days")).toHaveText("12days");
  await expect(page.getByTestId("proposed-days")).toContainText("6days");
  await expect(page.getByText("River fine-tuned model", { exact: true }).first()).toBeVisible();
  await page.screenshot({ path: "../docs/dashboard.png", fullPage: true });

  await page.getByRole("button", { name: "Before", exact: true }).click();
  await expect(page.getByText("Current workflow", { exact: true })).toBeVisible();
  await expect(page.getByText("Recommended workflow", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "After", exact: true }).click();
  await expect(page.getByText("Recommended workflow", { exact: true })).toBeVisible();
  await expect(page.getByText("Not required", { exact: true })).toHaveCount(2);
  await page.getByRole("button", { name: "Compare", exact: true }).click();

  await page.getByRole("button", { name: "Company policy", exact: true }).click();
  await expect(page.getByText("These are the only required approvals for an amount of $1,000 or less.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Model lab SFT", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Unseen examples, side by side" })).toBeVisible();
  await expect(page.locator(".evaluation-table tbody tr")).toHaveCount(5);
  await expect(page.getByText("river://", { exact: false }).first()).toBeVisible();
  await page.locator("details").first().locator("summary").click();
  await expect(page.locator("details").first().locator("pre")).toHaveCount(2);
  await page.screenshot({ path: "../docs/model-comparison.png", fullPage: true });

  await page.getByRole("button", { name: "Workflow overview", exact: true }).click();
  await page.getByLabel("Expense amount").fill("2600");
  await expect(page.getByText("Inputs changed.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Analyze workflow", exact: true }).click();
  await expect(page.getByTestId("saved-days")).toHaveText("3days / request");
  await expect(page.getByTestId("proposed-days")).toContainText("9days");
  await page.getByLabel("Receipt attached").uncheck();
  await page.getByRole("button", { name: "Analyze workflow", exact: true }).click();
  await expect(page.getByTestId("saved-days")).toHaveText("0days / request");
  await expect(page.getByRole("heading", { name: "Keep the controls. Get a review." })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export report", exact: true }).click();
  const download = await downloadPromise;
  const report = JSON.parse(await fs.readFile((await download.path())!, "utf8"));
  expect(report.analysis.engine).toBe("river");
  expect(report.analysis.model.checkpoint).toMatch(/^river:\/\//);
  expect(report.analysis.metrics.saved_days).toBe(0);
  expect(report.analysis.compliance.status).toBe("review_required");
  expect(errors).toEqual([]);
});

test("mobile navigation and workflow remain usable without page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByTestId("saved-days")).toHaveText("6days / request");
  const widths = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: window.innerWidth }));
  expect(widths.page).toBeLessThanOrEqual(widths.viewport + 1);
  await page.screenshot({ path: "../docs/mobile.png", fullPage: true });
  await page.getByRole("button", { name: "Company policy", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Employee reimbursement policy" })).toBeVisible();
  await page.getByRole("button", { name: "Model lab SFT", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your WorkflowDNA model" })).toBeVisible();
});
