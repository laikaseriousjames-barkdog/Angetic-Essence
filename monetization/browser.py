"""Phase 4: Playwright Browser Automation.

Automated browser interactions for deployment and data collection.
"""

from core.logger import setup_logger

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class BrowserAutomation:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("browser")
        self.playwright = None
        self.browser = None
        self.page = None

    def start(self):
        if sync_playwright is None:
            self.logger.warning(
                "Playwright not installed. Install with: "
                "pip install playwright && python -m playwright install"
            )
            return False
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
            self.logger.info("Browser started successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Browser start failed: {e}")
            return False

    def navigate(self, url: str) -> bool:
        if not self.page:
            self.logger.warning("Browser not started.")
            return False
        try:
            self.page.goto(url, wait_until="networkidle")
            self.logger.info(f"Navigated to {url}")
            return True
        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            return False

    def fill_and_submit(
        self, selector: str, value: str, submit_selector: str | None = None
    ) -> bool:
        if not self.page:
            return False
        try:
            self.page.fill(selector, value)
            if submit_selector:
                self.page.click(submit_selector)
            else:
                self.page.press(selector, "Enter")
            self.logger.info(f"Filled '{selector}' and submitted.")
            return True
        except Exception as e:
            self.logger.error(f"Form interaction failed: {e}")
            return False

    def screenshot(self, path: str = "screenshot.png") -> str | None:
        if not self.page:
            return None
        try:
            self.page.screenshot(path=path, full_page=True)
            self.logger.info(f"Screenshot saved to {path}")
            return path
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.logger.info("Browser closed.")
