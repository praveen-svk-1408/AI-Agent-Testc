"""Test crawl of login page."""
import asyncio
from app.services.crawler import crawl_page

async def test():
    snap = await crawl_page("http://localhost:3005/login")
    print("Title:", snap.page_title)
    print("Elements:", len(snap.elements))
    for e in snap.elements[:15]:
        txt = (e.text or "")[:40]
        print(f"  [{e.element_type}] selector={e.selector} text={txt!r}")
    print("Forms:", len(snap.forms))
    for f in snap.forms:
        print(f"  action={f.get('action')} fields={len(f.get('fields', []))}")
        for fld in f.get("fields", []):
            print(f"    {fld.get('tag')} name={fld.get('name')} type={fld.get('type')}")
    if snap.raw_html:
        # Check if React rendered
        idx = snap.raw_html.find('<div id="root">')
        if idx >= 0:
            print("\nroot div content (200 chars):")
            print(snap.raw_html[idx:idx+500])

asyncio.run(test())
