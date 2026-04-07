"""
Browser Crawl Tool (AgentCore Browser Tool).

Replaces the custom Playwright + MCP crawler from the original codebase.
Uses the AgentCore Browser Tool SDK to navigate pages, extract interactive elements,
and capture accessibility information.

Ported from: backend/app/services/crawler.py
"""

import json
import logging
from urllib.parse import urljoin

from schemas.agent import PageSnapshot, PageElement

logger = logging.getLogger(__name__)

# JavaScript to extract interactive elements from a page
# Ported from backend/app/services/crawler.py EXTRACT_ELEMENTS_JS
EXTRACT_ELEMENTS_JS = """
() => {
    const elements = [];
    const interactiveSelectors = [
        'a[href]', 'button', 'input', 'select', 'textarea',
        '[role="button"]', '[role="link"]', '[role="textbox"]',
        '[role="checkbox"]', '[role="radio"]', '[role="combobox"]',
        '[role="menuitem"]', '[role="tab"]', '[onclick]',
        '[data-testid]', '[aria-label]'
    ];

    const seen = new Set();
    for (const selector of interactiveSelectors) {
        for (const el of document.querySelectorAll(selector)) {
            if (seen.has(el)) continue;
            seen.add(el);

            const tag = el.tagName.toLowerCase();
            const role = el.getAttribute('role') || '';
            const text = (el.textContent || '').trim().substring(0, 100);
            const type = el.getAttribute('type') || '';
            const name = el.getAttribute('name') || '';
            const id = el.getAttribute('id') || '';
            const ariaLabel = el.getAttribute('aria-label') || '';
            const testId = el.getAttribute('data-testid') || '';
            const placeholder = el.getAttribute('placeholder') || '';
            const href = el.getAttribute('href') || '';
            const className = el.className || '';

            // Build a stable selector (priority: data-testid > id > name > role+text)
            let bestSelector = '';
            if (testId) bestSelector = `[data-testid="${testId}"]`;
            else if (id) bestSelector = `#${id}`;
            else if (name && tag === 'input') bestSelector = `${tag}[name="${name}"]`;
            else if (ariaLabel) bestSelector = `[aria-label="${ariaLabel}"]`;
            else if (role && text) bestSelector = `[role="${role}"]:has-text("${text.substring(0, 50)}")`;
            else if (tag === 'a' && text) bestSelector = `a:has-text("${text.substring(0, 50)}")`;
            else if (tag === 'button' && text) bestSelector = `button:has-text("${text.substring(0, 50)}")`;
            else bestSelector = `${tag}`;

            let elementType = tag;
            if (tag === 'input') elementType = type || 'text';
            else if (tag === 'a') elementType = 'link';

            const attrs = {};
            if (id) attrs['id'] = id;
            if (name) attrs['name'] = name;
            if (type) attrs['type'] = type;
            if (ariaLabel) attrs['aria-label'] = ariaLabel;
            if (testId) attrs['data-testid'] = testId;
            if (placeholder) attrs['placeholder'] = placeholder;
            if (href) attrs['href'] = href;
            if (className && typeof className === 'string')
                attrs['class'] = className.substring(0, 100);

            elements.push({
                tag, role, text, selector: bestSelector,
                element_type: elementType, attributes: attrs
            });
        }
    }

    // Extract forms
    const forms = [];
    for (const form of document.querySelectorAll('form')) {
        const fields = [];
        for (const field of form.querySelectorAll('input, select, textarea, button')) {
            const labelEl = field.id ?
                document.querySelector(`label[for="${field.id}"]`) : null;
            fields.push({
                tag: field.tagName.toLowerCase(),
                name: field.getAttribute('name') || '',
                type: field.getAttribute('type') || '',
                id: field.getAttribute('id') || '',
                label: labelEl ? labelEl.textContent.trim() : (field.getAttribute('aria-label') || ''),
            });
        }
        forms.push({
            action: form.getAttribute('action') || '',
            method: form.getAttribute('method') || 'GET',
            fields
        });
    }

    return { elements, forms, title: document.title };
}
"""


async def crawl_page_with_browser_tool(
    browser_tool,
    url: str,
) -> PageSnapshot:
    """Crawl a single page using the AgentCore Browser Tool.

    Args:
        browser_tool: The AgentCore Browser Tool instance.
        url: The URL to crawl.

    Returns a PageSnapshot with extracted elements and forms.
    """
    try:
        # Navigate to the page
        await browser_tool.navigate(url)

        # Extract elements using injected JavaScript
        result = await browser_tool.evaluate(EXTRACT_ELEMENTS_JS)
        data = json.loads(result) if isinstance(result, str) else result

        elements = [PageElement(**el) for el in data.get("elements", [])]
        forms = data.get("forms", [])
        title = data.get("title", "")

        # Get accessibility tree if available
        accessibility_tree = None
        try:
            accessibility_tree = await browser_tool.get_accessibility_tree()
        except Exception:
            pass

        return PageSnapshot(
            page_url=url,
            page_title=title,
            elements=elements,
            forms=forms,
            accessibility_tree=accessibility_tree,
        )

    except Exception as e:
        logger.error("Failed to crawl %s: %s", url, e)
        return PageSnapshot(page_url=url, page_title="Error", elements=[], forms=[])


async def crawl_pages(
    base_url: str,
    pages: list[str],
    browser_tool=None,
    login_url: str | None = None,
    login_username: str | None = None,
    login_password: str | None = None,
) -> list[PageSnapshot]:
    """Crawl multiple pages and extract interactive elements.

    Args:
        base_url: The base URL of the application.
        pages: List of relative URL paths to crawl.
        browser_tool: AgentCore Browser Tool instance. If None, uses a fallback approach.
        login_url: Optional login page URL for authentication.
        login_username: Optional login username.
        login_password: Optional login password.

    Returns a list of PageSnapshot objects.
    """
    if browser_tool is None:
        logger.warning("No browser tool provided — returning empty snapshots")
        return [
            PageSnapshot(page_url=urljoin(base_url, page), page_title="No browser available")
            for page in pages
        ]

    # Handle authentication if credentials provided
    if login_url and login_username and login_password:
        try:
            full_login_url = urljoin(base_url, login_url) if not login_url.startswith("http") else login_url
            await browser_tool.navigate(full_login_url)

            # Try common login form patterns
            # The actual field selectors will depend on the application
            await browser_tool.fill('input[name="email"], input[name="username"], input[type="email"]', login_username)
            await browser_tool.fill('input[name="password"], input[type="password"]', login_password)
            await browser_tool.click('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign in")')

            logger.info("Authentication completed for %s", login_url)
        except Exception as e:
            logger.warning("Authentication failed: %s — continuing without login", e)

    snapshots = []
    for page in pages:
        full_url = urljoin(base_url, page) if not page.startswith("http") else page
        snapshot = await crawl_page_with_browser_tool(browser_tool, full_url)
        snapshots.append(snapshot)
        logger.info("Crawled %s: %d elements, %d forms", full_url, len(snapshot.elements), len(snapshot.forms))

    return snapshots


async def load_crawl_snapshots(suite_id: str, snapshots_dir: str = "artifacts") -> list[PageSnapshot] | None:
    """Load pre-crawled snapshots from local filesystem (cache).

    Args:
        suite_id: The suite ID to load snapshots for.
        snapshots_dir: Base directory for stored crawl artifacts.

    Returns a list of PageSnapshot objects, or None if no cache exists.
    """
    import os

    suite_dir = os.path.join(snapshots_dir, suite_id)
    if not os.path.isdir(suite_dir):
        return None

    snapshots = []
    for filename in sorted(os.listdir(suite_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(suite_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    snapshots.append(PageSnapshot(**item))
            else:
                snapshots.append(PageSnapshot(**data))
        except Exception as e:
            logger.warning("Failed to load snapshot %s: %s", filepath, e)

    return snapshots if snapshots else None
