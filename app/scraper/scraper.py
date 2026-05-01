"""
Fetches a job posting URL and extracts: title, company, location, raw description.

Uses requests + BeautifulSoup. Playwright is used automatically if installed
and the page requires JavaScript rendering (optional dependency).
"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}


def scrape_url(url: str) -> dict:
    """
    Fetch a job posting URL and return a dict suitable for insert_job().
    Falls back to Playwright if BeautifulSoup gets no content.
    """
    html = _fetch_requests(url)

    # Try Playwright if the page looks JS-rendered (very little text)
    if len(html) < 2000:
        html = _fetch_playwright(url) or html

    return _parse_html(html, url)


def _fetch_requests(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"<html><body>Error fetching page: {e}</body></html>"


def _fetch_playwright(url: str) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=10000)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return None


def _parse_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml" if _lxml_available() else "html.parser")

    # Remove boilerplate
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title = _extract_title(soup)
    company = _extract_company(soup, url)
    location = _extract_location(soup)
    description = _extract_description(soup)

    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "raw_description": description,
        "skills": [],
        "experience_years": 0,
        "salary_min": 0,
        "salary_max": 0,
        "remote": False,
    }


def _extract_title(soup: BeautifulSoup) -> str:
    # Common job title selectors across major job boards
    selectors = [
        "h1.job-title", "h1.jobsearch-JobInfoHeader-title",
        "[data-testid='job-title']", ".job-title", "h1",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)[:200]

    title = soup.find("title")
    if title:
        text = title.get_text(strip=True)
        # Strip "at Company | Job Board" suffix patterns
        text = re.split(r"\s+(?:at|@|-|–|\|)\s+", text)[0]
        return text[:200]
    return "Unknown Title"


def _extract_company(soup: BeautifulSoup, url: str) -> str:
    selectors = [
        "[data-testid='company-name']", ".company-name",
        ".jobsearch-CompanyInfoContainer a", ".employer-name",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)[:100]

    # Fall back to domain name
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1).split(".")[0].title() if m else "Unknown Company"


def _extract_location(soup: BeautifulSoup) -> str:
    selectors = [
        "[data-testid='job-location']", ".job-location",
        ".jobsearch-JobInfoHeader-subtitle div", ".location",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)[:100]
    return ""


def _extract_description(soup: BeautifulSoup) -> str:
    selectors = [
        "#job-description", ".job-description",
        "[data-testid='job-description']", ".description",
        "article", "main",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 200:
                return text[:10000]

    return soup.get_text(separator="\n", strip=True)[:10000]


def _lxml_available() -> bool:
    try:
        import lxml
        return True
    except ImportError:
        return False
