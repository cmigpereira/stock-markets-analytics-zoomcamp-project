"""Local browser smoke test and real dashboard screenshots; run with app on port 8501."""

from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    target = Path("docs/screenshots")
    target.mkdir(parents=True, exist_ok=True)
    views = [
        ("Research overview", "The capital test", "overview"),
        ("Signal explorer", "Latest research signals", "signals"),
        ("Model evidence", "Six models. One controlled comparison.", "models"),
        ("Trade ledger", "Every entry has a cost", "trades"),
        ("Data & method", "Follow the evidence", "method"),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1512, "height": 1100}, device_scale_factor=1)
        page.goto("http://localhost:8501", wait_until="domcontentloaded")
        for view, heading, filename in views:
            page.get_by_text(view, exact=True).click()
            page.get_by_text(heading, exact=True).wait_for(timeout=60000)
            # Wait for Streamlit's running indicator to disappear and charts to render.
            page.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden", timeout=60000)
            if view != "Data & method":
                page.locator('[data-testid="stPlotlyChart"], [data-testid="stDataFrame"]').first.wait_for()
            errors = page.locator('[data-testid="stException"]')
            assert errors.count() == 0, errors.all_text_contents()
            page.screenshot(path=str(target / f"{filename}.png"), full_page=True)
            print(f"Verified {view}; captured {filename}.png")
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        mobile.goto("http://localhost:8501", wait_until="domcontentloaded")
        mobile.get_by_text("The capital test", exact=True).wait_for(timeout=60000)
        mobile.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden", timeout=60000)
        assert mobile.locator('[data-testid="stException"]').count() == 0
        mobile.screenshot(path=str(target / "mobile.png"), full_page=True)
        browser.close()


if __name__ == "__main__":
    main()
