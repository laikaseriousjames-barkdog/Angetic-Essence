"""Phase 4: Market Exploration - Web Scraping Module.

Scrapes web platforms for programmatic arbitrage, micro-SaaS opportunities,
and data-flipping niches.
"""

import json
import time
from datetime import datetime
from urllib.parse import urljoin
from core.logger import setup_logger

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class MarketScraper:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("scraper")
        self.targets = config.get("monetization", {}).get("target_marketplaces", [])
        self.session = requests.Session() if requests else None
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            }
        ) if self.session else None

    def scrape_url(self, url: str) -> dict:
        self.logger.info(f"Scraping: {url}")
        if not self.session:
            return {"url": url, "status": "no_requests_lib", "data": None}
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = {"url": url, "status": resp.status_code, "size": len(resp.text)}
            if BeautifulSoup and "text/html" in resp.headers.get("Content-Type", ""):
                soup = BeautifulSoup(resp.text, "lxml")
                data["title"] = soup.title.string if soup.title else None
                data["links"] = len(soup.find_all("a"))
                data["text_length"] = len(soup.get_text(strip=True))
            elif "application/json" in resp.headers.get("Content-Type", ""):
                data["json"] = resp.json()[:500]
            else:
                data["preview"] = resp.text[:500]
            self.logger.info(f"Scraped {url}: {data.get('title', data.get('status'))}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}")
            return {"url": url, "status": "error", "error": str(e)}

    def scan_opportunities(self) -> list[dict]:
        results = []
        for url in self.targets:
            result = self.scrape_url(url)
            if result.get("status") == 200:
                opp = self._analyze_opportunity(result)
                if opp:
                    results.append(opp)
            time.sleep(2)
        return results

    def _analyze_opportunity(self, data: dict) -> dict | None:
        """Identify monetization patterns."""
        return {
            "source": data.get("url"),
            "type": "data_flip" if data.get("json") else "content_aggregation",
            "confidence": 0.5,
            "timestamp": datetime.utcnow().isoformat(),
            "raw_preview": json.dumps(data.get("json") or data.get("preview", ""))[
                :300
            ],
        }
