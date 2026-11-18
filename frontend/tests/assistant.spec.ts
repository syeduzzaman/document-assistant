import { expect, test } from "@playwright/test";

test("sample question has inspectable source passages", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Retrieval demo", { exact: true })).toBeVisible();
  await expect(page.getByText("employee-handbook.md", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "How many days of annual leave do employees receive?" }).click();
  await page.getByRole("button", { name: "Ask question" }).click();
  const answer = page.getByRole("region", { name: "Answer", exact: true });
  await expect(answer).toContainText("30 days");
  await answer.locator("summary").first().click();
  await expect(answer.locator("blockquote").first()).toBeVisible();
});

test("upload, ask, and delete a new document", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Retrieval demo", { exact: true })).toBeVisible();
  await page.getByLabel("Upload document", { exact: true }).setInputFiles({
    name: "warranty.txt", mimeType: "text/plain",
    buffer: Buffer.from("The bicycle warranty lasts exactly 42 months."),
  });
  await expect(page.getByText("warranty.txt", { exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: /warranty.txt/ }).check();
  await page.getByLabel("Your question", { exact: true }).fill("How long does the bicycle warranty last?");
  await page.getByRole("button", { name: "Ask question" }).click();
  await expect(page.getByRole("region", { name: "Answer", exact: true })).toContainText("42 months");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete warranty.txt", exact: true }).click();
  await expect(page.getByText("warranty.txt", { exact: true })).toHaveCount(0);
});

test("unanswerable questions show an honest refusal", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Retrieval demo", { exact: true })).toBeVisible();
  await page.getByLabel("Your question", { exact: true }).fill("Which astronauts visited Jupiter?");
  await page.getByRole("button", { name: "Ask question" }).click();
  await expect(page.getByRole("heading", { name: "More information needed" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Answer", exact: true })).toContainText("couldn't find enough information");
});

test("sample repair checklist cites the current approval procedure and flags gaps", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Repair Estimate Checklist", exact: true }).click();
  await page.getByRole("button", { name: "Run sample case" }).click();
  const checklist = page.getByRole("region", { name: "Checklist results" });
  await expect(checklist.getByRole("heading", { name: "Photos", exact: true })).toBeVisible();
  await expect(checklist.getByRole("heading", { name: "Documents", exact: true })).toBeVisible();
  await expect(checklist.getByRole("heading", { name: "Approvals", exact: true })).toBeVisible();
  await expect(checklist.getByRole("heading", { name: "Needs manual confirmation" })).toBeVisible();
  await expect(checklist).toContainText("EUR 300");
  await expect(checklist).not.toContainText("EUR 500");
  await checklist.getByText(/Source supplement-approval-v2\.md/).click();
  await expect(checklist.locator("blockquote").filter({ hasText: "EUR 300" })).toBeVisible();
});
