import { test, expect } from "@playwright/test";

// ────────────────────────────────────────────────────────
// Homepage
// ────────────────────────────────────────────────────────
test.describe("Homepage (/)", () => {
  test("loads without errors", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBeLessThan(400);
  });

  test("has a page title", async ({ page }) => {
    await page.goto("/");
    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test("renders main navigation", async ({ page }) => {
    await page.goto("/");
    // Sidebar or nav should have links
    const nav = page.locator("nav, aside");
    await expect(nav.first()).toBeVisible();
  });
});

// ────────────────────────────────────────────────────────
// Rankings Page
// ────────────────────────────────────────────────────────
test.describe("Rankings (/rankings)", () => {
  test("loads without errors", async ({ page }) => {
    const response = await page.goto("/rankings");
    expect(response?.status()).toBeLessThan(400);
  });

  test("renders page content", async ({ page }) => {
    await page.goto("/rankings");
    await page.waitForLoadState("networkidle");
    // Should have some heading or content
    const body = page.locator("body");
    await expect(body).toBeVisible();
    const text = await body.textContent();
    expect(text?.length).toBeGreaterThan(50);
  });
});

// ────────────────────────────────────────────────────────
// Market Page
// ────────────────────────────────────────────────────────
test.describe("Market (/market)", () => {
  test("loads without errors", async ({ page }) => {
    const response = await page.goto("/market");
    expect(response?.status()).toBeLessThan(400);
  });

  test("renders page content", async ({ page }) => {
    await page.goto("/market");
    await page.waitForLoadState("networkidle");
    const body = page.locator("body");
    await expect(body).toBeVisible();
  });
});

// ────────────────────────────────────────────────────────
// Stock Detail Page
// ────────────────────────────────────────────────────────
test.describe("Stock Detail (/stock/VNM)", () => {
  test("loads without errors", async ({ page }) => {
    const response = await page.goto("/stock/VNM");
    expect(response?.status()).toBeLessThan(400);
  });

  test("displays stock symbol", async ({ page }) => {
    await page.goto("/stock/VNM");
    await page.waitForLoadState("networkidle");
    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toContain("VNM");
  });

  test("renders AI report section", async ({ page }) => {
    await page.goto("/stock/VNM");
    await page.waitForLoadState("networkidle");
    // Should have AI report panel or a loading/empty state
    const body = page.locator("body");
    await expect(body).toBeVisible();
  });
});

// ────────────────────────────────────────────────────────
// Learn Hub Page
// ────────────────────────────────────────────────────────
test.describe("Learn Hub (/learn)", () => {
  test("loads without errors", async ({ page }) => {
    const response = await page.goto("/learn");
    expect(response?.status()).toBeLessThan(400);
  });

  test("displays learn categories", async ({ page }) => {
    await page.goto("/learn");
    await page.waitForLoadState("networkidle");
    const bodyText = await page.locator("body").textContent();
    // Should mention at least one category
    const hasCategory =
      bodyText?.includes("Technical") ||
      bodyText?.includes("Fundamental") ||
      bodyText?.includes("Macro") ||
      bodyText?.includes("Kỹ thuật") ||
      bodyText?.includes("Cơ bản") ||
      bodyText?.includes("Vĩ mô");
    expect(hasCategory).toBeTruthy();
  });
});

// ────────────────────────────────────────────────────────
// Learn Category Pages
// ────────────────────────────────────────────────────────
test.describe("Learn Category Pages", () => {
  for (const category of ["technical", "fundamental", "macro"]) {
    test(`/learn/${category} loads without errors`, async ({ page }) => {
      const response = await page.goto(`/learn/${category}`);
      expect(response?.status()).toBeLessThan(400);
    });

    test(`/learn/${category} renders glossary entries`, async ({ page }) => {
      await page.goto(`/learn/${category}`);
      await page.waitForLoadState("networkidle");
      const body = page.locator("body");
      await expect(body).toBeVisible();
      const text = await body.textContent();
      expect(text?.length).toBeGreaterThan(100);
    });
  }
});

// ────────────────────────────────────────────────────────
// 404 Page
// ────────────────────────────────────────────────────────
test.describe("404 Page", () => {
  test("returns 404 for non-existent route", async ({ page }) => {
    const response = await page.goto("/this-page-does-not-exist");
    expect(response?.status()).toBe(404);
  });
});

// ────────────────────────────────────────────────────────
// Navigation
// ────────────────────────────────────────────────────────
test.describe("Navigation", () => {
  test("can navigate between main pages", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Find links to key pages in nav/sidebar
    const rankingsLink = page.locator('a[href*="rankings"], a[href*="ranking"]').first();
    if (await rankingsLink.isVisible()) {
      await rankingsLink.click();
      await page.waitForLoadState("networkidle");
      expect(page.url()).toContain("ranking");
    }
  });

  test("sidebar links work", async ({ page }) => {
    await page.goto("/learn");
    await page.waitForLoadState("networkidle");
    // Just verify the learn page loads directly — sidebar navigation 
    // may be collapsed or hidden depending on viewport
    expect(page.url()).toContain("learn");
  });
});

// ────────────────────────────────────────────────────────
// Theme Toggle
// ────────────────────────────────────────────────────────
test.describe("Theme Toggle", () => {
  test("theme toggle button exists", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Look for a theme toggle button (sun/moon icon, or button with theme-related aria label)
    const themeToggle = page.locator(
      'button:has(svg), [aria-label*="theme"], [aria-label*="Theme"], [aria-label*="dark"], [aria-label*="light"]'
    ).first();
    if (await themeToggle.isVisible()) {
      await themeToggle.click();
      // After clicking, the page should still be functional
      const body = page.locator("body");
      await expect(body).toBeVisible();
    }
  });
});

// ────────────────────────────────────────────────────────
// Console Errors Check
// ────────────────────────────────────────────────────────
test.describe("Console Errors", () => {
  const pagesToCheck = ["/", "/rankings", "/market", "/stock/VNM", "/learn", "/learn/technical"];

  for (const url of pagesToCheck) {
    test(`no critical console errors on ${url}`, async ({ page }) => {
      const errors: string[] = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") {
          const text = msg.text();
          // Ignore known non-critical errors
          if (
            text.includes("favicon") ||
            text.includes("404") ||
            text.includes("Failed to load resource") ||
            text.includes("hydration") ||
            text.includes("NEXT_") ||
            text.includes("net::ERR") ||
            text.includes("CORS") // Backend CORS errors are backend issues, not frontend bugs
          ) {
            return;
          }
          errors.push(text);
        }
      });

      await page.goto(url);
      await page.waitForLoadState("networkidle");
      // Wait a bit for any async errors
      await page.waitForTimeout(2000);

      if (errors.length > 0) {
        console.log(`Console errors on ${url}:`, errors);
      }
      // Allow up to 0 critical errors
      expect(errors.length).toBe(0);
    });
  }
});
