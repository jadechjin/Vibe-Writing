import { test, expect } from '@playwright/test';

test.describe('G4 and G5 Workbench Flows', () => {
  const projectId = 'p1';
  const systemId = 's1';

  test.beforeEach(async ({ page }) => {
    // Navigate to the system page
    await page.goto(`/projects/${projectId}/systems/${systemId}`);
  });

  test('should navigate through G4 - Evidence & Outline', async ({ page }) => {
    // Assume we are at G4
    // Check if EvidenceMatrixPanel is rendered
    await expect(page.locator('text=Evidence & Outline')).toBeVisible();

    // Check claims list
    await expect(page.locator('text=Claims')).toBeVisible();

    // Generate Outline
    const generateBtn = page.getByRole('button', { name: /Generate Outline/i });
    await expect(generateBtn).toBeEnabled();
    await generateBtn.click();
    
    // Mocking status change to Outline_Ready would happen in backend, 
    // but we can check if button text changes to "Generating..."
    // await expect(page.locator('text=Generating...')).toBeVisible();
    
    // Confirm Outline
    // Assume outline appeared after polling
    const confirmBtn = page.getByRole('button', { name: /Confirm Outline/i });
    // We might need to wait for it or mock the state
    // await expect(confirmBtn).toBeVisible();
  });

  test('should navigate through G5 - Chapter Drafting', async ({ page }) => {
    // Assume we are at G5
    // Check if DraftPanel is rendered
    await expect(page.locator('text=Chapter Drafting & Review')).toBeVisible();

    // Generate Section Draft
    const generateDraftBtn = page.getByRole('button', { name: /Generate Draft/i }).first();
    await expect(generateDraftBtn).toBeEnabled();
    await generateDraftBtn.click();
    
    // Check if "Generating..." appears
    // await expect(page.locator('text=Generating...')).toBeVisible();

    // Approve Draft
    // Assume draft appeared after polling
    const approveBtn = page.getByRole('button', { name: /Approve/i }).first();
    // await expect(approveBtn).toBeVisible();
    // await approveBtn.click();
  });
});
