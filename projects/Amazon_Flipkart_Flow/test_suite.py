import pytest
from playwright.sync_api import sync_playwright, expect

@pytest.mark.parametrize("url", ['https://dudekulabadesaheb.github.io/kpdbc/index.html', 'https://dudekulabadesaheb.github.io/kpdbc/about.html', 'https://dudekulabadesaheb.github.io/kpdbc/web-coding.html', 'https://dudekulabadesaheb.github.io/kpdbc/custom-programming.html', 'https://dudekulabadesaheb.github.io/kpdbc/wordpress-development.html', 'https://dudekulabadesaheb.github.io/kpdbc/start-project.html', 'https://dudekulabadesaheb.github.io/kpdbc/seo.html', 'https://dudekulabadesaheb.github.io/kpdbc/social-media-marketing.html', 'https://dudekulabadesaheb.github.io/kpdbc/content-marketing.html', 'https://dudekulabadesaheb.github.io/kpdbc/google-online-advertising.html', 'https://dudekulabadesaheb.github.io/kpdbc/social-media-brand-promotion.html', 'https://dudekulabadesaheb.github.io/kpdbc/local-digital-marketing.html', 'https://dudekulabadesaheb.github.io/kpdbc/website-digital-presence-optimization.html', 'https://dudekulabadesaheb.github.io/kpdbc/analytics-performance-monitoring.html'])
def test_application_flow(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            geolocation={"latitude": 12.9716, "longitude": 77.5946},
            permissions=["geolocation"]
        )
        page = context.new_page()
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")

        # Handle Location / Delivery Modal if present
        pincode_input = page.locator("input[placeholder*='pincode'], input[id*='GLUXZipUpdateInput']")
        if pincode_input.count() > 0:
            pincode_input.first.fill("562114")
            page.locator("button:has-text('Apply')").first.click()

        expect(page.locator("body")).to_be_visible()
        browser.close()
