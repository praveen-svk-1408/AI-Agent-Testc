import { test, expect } from '@playwright/test';

test.describe('E-suite', () => {
  test('Test Login', async ({ page }) => {
    await page.goto('http://localhost:3005/');
    await page.waitForLoadState('networkidle');

    await page.locator('#email').fill('test@example.com');

    await page.locator('#password').fill('password123');

    await page.locator('#login-button').click();

    await page.waitForURL('/');

    await expect(page.locator('#logo')).toBeVisible();

    await expect(page.locator('text=Welcome to TechStore')).toContainText('');

    await page.screenshot({ path: 'login_success.png', fullPage: true });

  });
});
