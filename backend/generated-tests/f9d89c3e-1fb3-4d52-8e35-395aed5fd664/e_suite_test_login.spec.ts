import { test, expect } from '@playwright/test';

test.describe('E-suite', () => {
  test('Test Login', async ({ page }) => {
    // Navigate to the login page
    await page.goto('http://localhost:3005/');
    await page.waitForLoadState('networkidle');

    // Wait for the page to load
    await page.waitForSelector('#login-link');

    // Enter valid email
    await page.locator('#email').fill('test@example.com');

    // Enter valid password
    await page.locator('#password').fill('password123');

    // Click the login button
    await page.locator('#login-button').click();

    // Wait for the page to load after login
    await page.waitForSelector('#logo');

    // Verify user is redirected to the home page
    await expect(page.locator('url')).toBeVisible();

    // Verify products are listed on the home page
    await expect(page.locator('#view-product-1')).toBeVisible();

    // Verify login button is not visible on the home page
    await expect(page.locator('#login-button')).toBeVisible();

    // Navigate to the login page with invalid credentials
    await page.goto('http://localhost:3005/');
    await page.waitForLoadState('networkidle');

    // Wait for the page to load
    await page.waitForSelector('#login-link');

    // Enter invalid email
    await page.locator('#email').fill('invalid@example.com');

    // Enter valid password
    await page.locator('#password').fill('password123');

    // Click the login button
    await page.locator('#login-button').click();

    // Verify login failed with invalid email
    await expect(page.locator('#email')).toBeVisible();

    // Navigate to the login page with empty fields
    await page.goto('http://localhost:3005/');
    await page.waitForLoadState('networkidle');

    // Wait for the page to load
    await page.waitForSelector('#login-link');

    // Enter empty email
    await page.locator('#email').fill('');

    // Enter empty password
    await page.locator('#password').fill('');

    // Click the login button
    await page.locator('#login-button').click();

    // Verify login failed with empty fields
    await expect(page.locator('#email')).toBeVisible();

  });
});
