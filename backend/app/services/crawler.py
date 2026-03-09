"""
Page Crawler using Playwright.

Crawls a target URL and extracts DOM structure, interactive elements,
form structures, and selectors for use by the Step Generator Agent.

Runs Playwright in a separate subprocess to avoid Windows asyncio event loop
conflicts (NotImplementedError with ProactorEventLoop when sync_playwright()
is called from within FastAPI/uvicorn's running event loop context).
"""

import asyncio
import json
import logging
import subprocess
import sys
import textwrap

from urllib.parse import urljoin

from app.config import get_settings
from app.schemas.agent import PageSnapshot, PageElement

logger = logging.getLogger(__name__)

settings = get_settings()


# Self-contained crawler script that runs in a separate process.
# It imports only playwright (no app dependencies), crawls the URL,
# and prints a JSON result to stdout.
_CRAWLER_SCRIPT = textwrap.dedent(r'''
import json
import sys

def main():
    url = sys.argv[1]
    timeout_ms = int(sys.argv[2]) if len(sys.argv) > 2 else 30000

    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

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

            results.push({ tag, role, text: text || null, selector, element_type: elementType, attributes: attrs });
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
                fields: fields,
            });
        });
        return forms;
    }
    """

    result = {"page_url": url, "page_title": None, "elements": [], "forms": [], "raw_html": None}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="AI-Agent-Test Crawler/1.0",
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PWTimeoutError:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                except PWTimeoutError:
                    browser.close()
                    print(json.dumps(result))
                    return

            result["page_title"] = page.title()

            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except PWTimeoutError:
                pass

            # Wait for SPA frameworks to render content
            try:
                page.wait_for_function(
                    """() => {
                        const root = document.getElementById('root') || document.getElementById('app') || document.getElementById('__next');
                        return !root || root.children.length > 0;
                    }""",
                    timeout=5000,
                )
            except PWTimeoutError:
                pass

            page.wait_for_timeout(2000)

            result["elements"] = page.evaluate(EXTRACT_ELEMENTS_JS)
            result["forms"] = page.evaluate(EXTRACT_FORMS_JS)

            raw_html = page.content()
            if len(raw_html) > 50000:
                raw_html = raw_html[:50000] + "\n<!-- truncated -->"
            result["raw_html"] = raw_html

            browser.close()
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result))

if __name__ == "__main__":
    main()
''')

# JavaScript to extract interactive elements from the page
EXTRACT_ELEMENTS_JS = """
() => {
    const results = [];
    const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [onclick]';
    const elements = document.querySelectorAll(interactiveSelectors);

    elements.forEach((el, index) => {
        if (index > 200) return; // Cap at 200 elements

        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return; // Skip hidden elements

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

        // Build best selector (prefer stable selectors)
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
        if (i > 20) return; // Cap at 20 forms
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


async def crawl_page(url: str) -> PageSnapshot:
    """
    Crawl a single page by running Playwright in a separate subprocess.
    This avoids Windows asyncio event loop conflicts when called from
    within FastAPI/uvicorn's running event loop.
    """
    logger.info("Crawling page: %s", url)

    timeout_ms = settings.crawler_timeout_ms
    # subprocess timeout = crawler timeout + buffer for startup/shutdown
    proc_timeout = (timeout_ms / 1000) + 30

    def _run_subprocess():
        proc = subprocess.run(
            [sys.executable, "-c", _CRAWLER_SCRIPT, url, str(timeout_ms)],
            capture_output=True,
            text=True,
            timeout=proc_timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Crawler subprocess failed (exit {proc.returncode}): {proc.stderr[:500]}"
            )
        return proc.stdout

    try:
        stdout = await asyncio.to_thread(_run_subprocess)
        data = json.loads(stdout)

        if "error" in data and data["error"]:
            logger.warning("Crawler reported error for %s: %s", url, data["error"])

        elements = [PageElement(**el) for el in data.get("elements", [])]

        snapshot = PageSnapshot(
            page_url=data.get("page_url", url),
            page_title=data.get("page_title"),
            elements=elements,
            forms=data.get("forms", []),
            raw_html=data.get("raw_html"),
        )

        logger.info("Crawled %s: %d elements, %d forms",
                     url, len(snapshot.elements), len(snapshot.forms))
        return snapshot

    except subprocess.TimeoutExpired:
        logger.error("Crawler subprocess timed out for %s", url)
        return PageSnapshot(page_url=url, page_title=None, elements=[], forms=[])
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse crawler output for %s: %s", url, str(e))
        return PageSnapshot(page_url=url, page_title=None, elements=[], forms=[])


async def crawl_pages(base_url: str, paths: list[str]) -> list[PageSnapshot]:
    """
    Crawl multiple pages given a base URL and list of relative paths.
    """
    snapshots = []
    for path in paths:
        if path.startswith("http"):
            url = path
        else:
            url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        try:
            snapshot = await crawl_page(url)
            snapshots.append(snapshot)
        except Exception as e:
            logger.error("Failed to crawl %s: %s", url, str(e), exc_info=True)
            snapshots.append(PageSnapshot(
                page_url=url,
                page_title=None,
                elements=[],
                forms=[],
            ))
    return snapshots
