"""
Page Crawler using Playwright (Python).

Crawls a target URL and extracts DOM structure, interactive elements,
form structures, and selectors for use by the Step Generator Agent.

Uses playwright.sync_api in a background thread (via asyncio.to_thread)
to avoid Windows ProactorEventLoop conflicts with FastAPI/uvicorn.
"""

import asyncio
import logging
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, BrowserContext, Browser

from app.config import get_settings
from app.schemas.agent import PageSnapshot, PageElement

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# JavaScript extraction snippets (evaluated inside the Playwright page)
# ---------------------------------------------------------------------------

EXTRACT_ELEMENTS_JS = """
() => {
    const results = [];
    const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [onclick]';
    const elements = document.querySelectorAll(interactiveSelectors);

    elements.forEach((el, index) => {
        if (index > 200) return;

        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;

        const tag = el.tagName.toLowerCase();
        const role = el.getAttribute('role') || null;
        const text = (el.textContent || '').trim().substring(0, 200);
        const ariaLabel = el.getAttribute('aria-label') || null;
        const testId = el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null;
        const name = el.getAttribute('name') || null;
        const id = el.getAttribute('id') || null;
        const type = el.getAttribute('type') || null;
        const placeholder = el.getAttribute('placeholder') || null;
        const href = el.getAttribute('href') || null;

        let selector = '';
        if (testId) {
            selector = `[data-testid="${testId}"]`;
        } else if (role && ariaLabel) {
            selector = `role=${role}[name="${ariaLabel}"]`;
        } else if (role && text && text.length < 50) {
            selector = `role=${role}[name="${text}"]`;
        } else if (ariaLabel) {
            selector = `[aria-label="${ariaLabel}"]`;
        } else if (id) {
            selector = `#${id}`;
        } else if (name) {
            selector = `${tag}[name="${name}"]`;
        } else if (placeholder) {
            selector = `${tag}[placeholder="${placeholder}"]`;
        } else if (text && text.length < 50) {
            selector = `text="${text}"`;
        } else {
            selector = `${tag}:nth-of-type(${index + 1})`;
        }

        let elementType = tag;
        if (tag === 'input') elementType = type ? `input-${type}` : 'input-text';
        if (tag === 'a') elementType = 'link';
        if (tag === 'button' || role === 'button') elementType = 'button';

        const attrs = {};
        if (href) attrs['href'] = href;
        if (type) attrs['type'] = type;
        if (name) attrs['name'] = name;
        if (placeholder) attrs['placeholder'] = placeholder;
        if (id) attrs['id'] = id;
        if (ariaLabel) attrs['aria-label'] = ariaLabel;

        results.push({
            tag,
            role,
            text: text || null,
            selector,
            element_type: elementType,
            attributes: attrs,
        });
    });

    return results;
}
"""

EXTRACT_FORMS_JS = """
() => {
    const forms = [];
    document.querySelectorAll('form').forEach((form, i) => {
        if (i > 20) return;
        const fields = [];
        form.querySelectorAll('input, select, textarea').forEach(field => {
            fields.push({
                tag: field.tagName.toLowerCase(),
                name: field.getAttribute('name') || null,
                type: field.getAttribute('type') || null,
                placeholder: field.getAttribute('placeholder') || null,
                required: field.hasAttribute('required'),
                label: field.getAttribute('aria-label') ||
                       (field.id && document.querySelector(`label[for="${field.id}"]`)?.textContent?.trim()) || null,
            });
        });
        forms.push({
            action: form.getAttribute('action') || null,
            method: form.getAttribute('method') || 'get',
            fields,
        });
    });
    return forms;
}
"""


# ---------------------------------------------------------------------------
# Playwright crawler (runs sync API in a thread)
# ---------------------------------------------------------------------------

def _new_context(browser: Browser) -> BrowserContext:
    """Create a fresh browser context with standard viewport / UA."""
    return browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="AI-Agent-Test Crawler/1.0",
    )


def _perform_login_sync(
    context: BrowserContext,
    login_url: str,
    username: str,
    password: str,
    timeout_ms: int,
) -> None:
    """
    Perform a standard form-based login using the given browser context.

    Auto-detects username (email/text input) and password fields on the
    login page, fills them, and submits the form.  After submission the
    cookies / session persist in *context* for all subsequent pages.
    """
    page = context.new_page()
    try:
        page.goto(login_url, wait_until="networkidle", timeout=timeout_ms)
    except PWTimeoutError:
        page.goto(login_url, wait_until="domcontentloaded", timeout=timeout_ms)

    # Wait for SPA rendering
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PWTimeoutError:
        pass
    page.wait_for_timeout(1000)

    # --- Auto-detect form fields ---
    # Password field
    pw_locator = page.locator('input[type="password"]:visible').first
    pw_locator.wait_for(state="visible", timeout=10000)

    # Username field: visible text/email/tel input that is NOT the password
    username_locator = page.locator(
        'input:visible:not([type="password"]):not([type="hidden"])'
        ':not([type="checkbox"]):not([type="radio"])'
        ':not([type="submit"]):not([type="button"])'
    ).first

    # Fill credentials
    username_locator.fill(username)
    pw_locator.fill(password)

    # Submit: try the nearest submit button first, else press Enter
    submit_btn = page.locator(
        'button[type="submit"]:visible, input[type="submit"]:visible'
    ).first
    if submit_btn.count():
        submit_btn.click()
    else:
        pw_locator.press("Enter")

    # Wait for navigation away from the login page
    try:
        page.wait_for_url(
            lambda url: url != login_url and "/login" not in url.lower(),
            timeout=15000,
        )
    except PWTimeoutError:
        logger.warning("Login redirect detection timed out — continuing anyway")

    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PWTimeoutError:
        pass

    logger.info("Login complete — current URL: %s", page.url)
    page.close()


def _extract_page_sync(
    context: BrowserContext,
    url: str,
    timeout_ms: int,
) -> PageSnapshot:
    """Navigate to *url* inside the (possibly authenticated) context and extract DOM info."""
    page = context.new_page()

    # Navigate – try networkidle first, fall back to domcontentloaded
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    except PWTimeoutError:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except PWTimeoutError:
            page.close()
            return PageSnapshot(page_url=url, page_title=None, elements=[], forms=[])

    page_title = page.title()

    # Extra settle time for late network activity
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PWTimeoutError:
        pass

    # Wait for SPA frameworks to render
    try:
        page.wait_for_function(
            """() => {
                const root = document.getElementById('root')
                    || document.getElementById('app')
                    || document.getElementById('__next');
                return !root || root.children.length > 0;
            }""",
            timeout=5000,
        )
    except PWTimeoutError:
        pass

    page.wait_for_timeout(2000)

    # Extract interactive elements & forms via JS evaluation
    raw_elements = page.evaluate(EXTRACT_ELEMENTS_JS)
    raw_forms = page.evaluate(EXTRACT_FORMS_JS)

    raw_html = page.content()
    if len(raw_html) > 50000:
        raw_html = raw_html[:50000] + "\n<!-- truncated -->"

    elements = [PageElement(**el) for el in raw_elements]

    page.close()
    return PageSnapshot(
        page_url=url,
        page_title=page_title,
        elements=elements,
        forms=raw_forms,
        raw_html=raw_html,
    )


def _crawl_pages_sync(
    urls: list[str],
    timeout_ms: int,
    login_url: str | None = None,
    login_username: str | None = None,
    login_password: str | None = None,
) -> list[PageSnapshot]:
    """
    Crawl one or more pages using a single Playwright browser.

    If login credentials are provided the crawler first authenticates via
    form-based login so subsequent page visits use the authenticated session.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = _new_context(browser)

            # Authenticate if credentials provided
            if login_url and login_username and login_password:
                logger.info("Performing login at %s as %s", login_url, login_username)
                try:
                    _perform_login_sync(
                        context, login_url, login_username, login_password, timeout_ms
                    )
                except Exception as e:
                    logger.error("Login failed: %s — continuing unauthenticated", e)

            # Crawl each page with the (possibly authenticated) context
            snapshots: list[PageSnapshot] = []
            for url in urls:
                try:
                    snap = _extract_page_sync(context, url, timeout_ms)
                    snapshots.append(snap)
                    logger.info(
                        "Crawled %s: %d elements, %d forms",
                        url, len(snap.elements), len(snap.forms),
                    )
                except Exception as e:
                    logger.error("Failed to crawl %s: %s", url, e, exc_info=True)
                    snapshots.append(
                        PageSnapshot(page_url=url, page_title=None, elements=[], forms=[])
                    )
            return snapshots
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def crawl_page(
    url: str,
    *,
    login_url: str | None = None,
    login_username: str | None = None,
    login_password: str | None = None,
) -> PageSnapshot:
    """
    Crawl a single page using Playwright.
    Optionally authenticates first if login credentials are provided.
    """
    logger.info("Crawling page: %s", url)
    timeout_ms = settings.crawler_timeout_ms

    try:
        snapshots = await asyncio.to_thread(
            _crawl_pages_sync,
            [url],
            timeout_ms,
            login_url,
            login_username,
            login_password,
        )
        return snapshots[0]
    except Exception as e:
        logger.error("Crawler failed for %s: %s", url, e, exc_info=True)
        return PageSnapshot(page_url=url, page_title=None, elements=[], forms=[])


async def crawl_pages(
    base_url: str,
    paths: list[str],
    *,
    login_url: str | None = None,
    login_username: str | None = None,
    login_password: str | None = None,
) -> list[PageSnapshot]:
    """
    Crawl multiple pages given a base URL and list of relative paths.
    Uses a single browser + context so authentication persists across pages.
    """
    urls = []
    for path in paths:
        if path.startswith("http"):
            urls.append(path)
        else:
            urls.append(urljoin(base_url.rstrip("/") + "/", path.lstrip("/")))

    timeout_ms = settings.crawler_timeout_ms
    try:
        return await asyncio.to_thread(
            _crawl_pages_sync,
            urls,
            timeout_ms,
            login_url,
            login_username,
            login_password,
        )
    except Exception as e:
        logger.error("Crawler batch failed: %s", e, exc_info=True)
        return [
            PageSnapshot(page_url=u, page_title=None, elements=[], forms=[])
            for u in urls
        ]
