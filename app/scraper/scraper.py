"""
Scrapes job postings from URLs.

Routing logic:
  1. Detect the ATS platform from the URL
  2. Use a platform-specific extractor (Greenhouse, Lever, Ashby, Workday)
  3. Fall back to generic BeautifulSoup extraction
  4. Fall back to Playwright if the page appears JS-rendered

Supported platforms:
  - LinkedIn     linkedin.com/jobs/view/... (works when logged in via browser session)
  - Greenhouse   boards.greenhouse.io, <company>.greenhouse.io
  - Lever        jobs.lever.co
  - Ashby        jobs.ashbyhq.com
  - Workday      <company>.myworkdayjobs.com  (requires Playwright)
  - Generic      any other URL
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_url(url: str) -> dict:
    """Main entry point. Returns a dict ready for insert_job()."""
    host = urlparse(url).netloc.lower()

    if "linkedin.com" in host:
        result = _scrape_linkedin(url)
    elif "indeed.com" in host:
        result = _scrape_indeed(url)
    elif "greenhouse.io" in host:
        result = _scrape_greenhouse(url)
    elif "lever.co" in host:
        result = _scrape_lever(url)
    elif "ashbyhq.com" in host:
        result = _scrape_ashby(url)
    elif "myworkdayjobs.com" in host:
        result = _scrape_workday(url)
    elif "ziprecruiter.com" in host:
        result = _scrape_ziprecruiter(url)
    else:
        result = _scrape_generic(url)

    # Ensure required keys exist
    result.setdefault("url", url)
    result.setdefault("skills", [])
    result.setdefault("experience_years", 0)
    result.setdefault("salary_min", 0)
    result.setdefault("salary_max", 0)
    result.setdefault("remote", False)
    result.setdefault("location", "")
    result.setdefault("raw_description", "")
    return result


# ---------------------------------------------------------------------------
# LinkedIn  (linkedin.com/jobs/view/...)
# ---------------------------------------------------------------------------

def _scrape_linkedin(url: str) -> dict:
    html = _fetch(url)
    if not html:
        return _fallback(url)
    soup = _make_soup(html)

    # Title — LinkedIn uses multiple possible containers depending on logged-in state
    title = (
        _text(soup, ".jobs-unified-top-card__job-title h1")
        or _text(soup, ".job-details-jobs-unified-top-card__job-title h1")
        or _text(soup, "h1.topcard__title")
        or _text(soup, "h1")
    )

    # Company — try every selector LinkedIn has used across versions
    company = (
        _text(soup, ".jobs-unified-top-card__company-name a")
        or _text(soup, ".jobs-unified-top-card__company-name")
        or _text(soup, ".job-details-jobs-unified-top-card__company-name a")
        or _text(soup, ".job-details-jobs-unified-top-card__company-name")
        or _text(soup, ".topcard__org-name-link")
        or _text(soup, ".topcard__flavor a")
        or _text(soup, '[data-tracking-control-name="public_jobs_topcard-org-name"]')
    )

    # Fall back: parse "<title>Job Title at Company | LinkedIn"
    if not company:
        page_title = soup.find("title")
        if page_title:
            m = re.search(r" at (.+?) (?:\||–|-)", page_title.get_text())
            if m:
                company = m.group(1).strip()

    # Location
    location = (
        _text(soup, ".jobs-unified-top-card__bullet")
        or _text(soup, ".job-details-jobs-unified-top-card__bullet")
        or _text(soup, ".topcard__flavor--bullet")
    )
    # Location field sometimes includes "· Remote" — split it off
    if location and "·" in location:
        location = location.split("·")[0].strip()

    remote = "remote" in (location or "").lower()

    # Description
    desc_el = (
        soup.select_one(".jobs-description__content")
        or soup.select_one(".jobs-box__html-content")
        or soup.select_one(".description__text")
        or soup.select_one("#job-details")
        or soup.select_one("main")
    )
    description = desc_el.get_text("\n", strip=True)[:10000] if desc_el else ""

    # Apply URL — use the company's site if not Easy Apply
    apply_url = _linkedin_apply_url(soup, url)

    return {
        "title": title or "Unknown",
        "company": company or "Unknown",
        "location": location or "",
        "raw_description": description,
        "remote": remote,
        "url": apply_url,
    }


def _linkedin_apply_url(soup: BeautifulSoup, linkedin_url: str) -> str:
    """
    Returns the external company apply URL if available, otherwise the LinkedIn URL.

    LinkedIn embeds job data as JSON inside <code> tags. The applyMethod field
    tells us whether it's Easy Apply or an offsite link.
    """
    # Strategy 1: dig through LinkedIn's embedded JSON blobs in <code> tags
    for code_tag in soup.find_all("code"):
        text = code_tag.string or ""
        if "applyMethod" not in text and "companyApplyUrl" not in text:
            continue
        try:
            data = json.loads(text)
            url = _dig_for_apply_url(data)
            if url:
                return url
        except (json.JSONDecodeError, TypeError):
            continue

    # Strategy 2: look for <script type="application/json"> blobs
    for script in soup.find_all("script", type="application/json"):
        text = script.string or ""
        if "companyApplyUrl" not in text and "applyUrl" not in text:
            continue
        try:
            data = json.loads(text)
            url = _dig_for_apply_url(data)
            if url:
                return url
        except (json.JSONDecodeError, TypeError):
            continue

    # Strategy 3: look for an apply <a> that points to a non-LinkedIn domain
    for sel in [
        '.jobs-apply-button--top-card a[href]',
        '.jobs-s-apply a[href]',
        'a[data-tracking-control-name*="apply"][href]',
    ]:
        el = soup.select_one(sel)
        if el:
            href = el.get("href", "")
            if href and "linkedin.com" not in href and href.startswith("http"):
                return href

    # Strategy 4: check if the apply button says "Easy Apply" — if not, note it's external
    # but we couldn't find the URL; fall back to the LinkedIn URL
    apply_btn_text = (
        _text(soup, ".jobs-apply-button--top-card")
        or _text(soup, ".jobs-s-apply button")
    ).lower()

    # If it's clearly Easy Apply, LinkedIn URL is correct
    # If it's external but we couldn't find the URL, still return LinkedIn URL as fallback
    return linkedin_url


def _dig_for_apply_url(data) -> str:
    """Recursively search a JSON structure for a company apply URL."""
    if isinstance(data, dict):
        # Direct keys LinkedIn uses
        for key in ("companyApplyUrl", "applyUrl", "externalApplyLink"):
            if key in data and isinstance(data[key], str) and data[key].startswith("http"):
                url = data[key]
                # Skip LinkedIn's own tracking redirects that loop back
                if "linkedin.com/jobs/view" not in url:
                    return url
        # Check applyMethod structure:
        # {"com.linkedin.voyager.jobs.OffsiteApply": {"companyApplyUrl": "..."}}
        for v in data.values():
            result = _dig_for_apply_url(v)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = _dig_for_apply_url(item)
            if result:
                return result
    return ""


# ---------------------------------------------------------------------------
# Greenhouse  (boards.greenhouse.io/company/jobs/ID or company.greenhouse.io)
# ---------------------------------------------------------------------------

def _scrape_greenhouse(url: str) -> dict:
    html = _fetch(url)
    if not html:
        return _fallback(url)
    soup = _make_soup(html)

    title = _text(soup, "h1.app-title") or _text(soup, "h1")
    company = _text(soup, ".company-name") or _text(soup, "a.company-name")

    # Greenhouse embeds a JSON-LD schema block
    ld = _extract_json_ld(soup)
    if ld:
        title    = title or ld.get("title", "")
        company  = company or (ld.get("hiringOrganization") or {}).get("name", "")
        location_raw = ld.get("jobLocation") or {}
        if isinstance(location_raw, list):
            location_raw = location_raw[0] if location_raw else {}
        location = (location_raw.get("address") or {}).get("addressLocality", "")
    else:
        location = _text(soup, ".location")

    desc_el = soup.select_one("#content") or soup.select_one(".job-description") or soup.select_one("main")
    description = desc_el.get_text("\n", strip=True)[:10000] if desc_el else ""

    if not company:
        # Extract from URL: boards.greenhouse.io/<company>/...
        m = re.search(r"greenhouse\.io/([^/]+)", url)
        company = m.group(1).replace("-", " ").title() if m else "Unknown"

    return {"title": title or "Unknown", "company": company, "location": location,
            "raw_description": description}


# ---------------------------------------------------------------------------
# Lever  (jobs.lever.co/company/uuid)
# ---------------------------------------------------------------------------

def _scrape_lever(url: str) -> dict:
    # Lever has a clean JSON API
    api_url = re.sub(r"jobs\.lever\.co/([^/]+)/([^/?]+).*",
                     r"api.lever.co/v0/postings/\1/\2", url)
    if "api.lever.co" in api_url:
        try:
            data = requests.get(api_url, headers=HEADERS, timeout=10).json()
            desc_html = (data.get("descriptionBody") or data.get("description") or "")
            soup = BeautifulSoup(desc_html, "html.parser")
            description = soup.get_text("\n", strip=True)[:10000]
            loc = data.get("categories", {}).get("location", "") or data.get("text", "")
            commitment = data.get("categories", {}).get("commitment", "")
            remote = "remote" in (loc + " " + commitment).lower()
            # Extract company from URL
            m = re.search(r"lever\.co/([^/]+)", url)
            company = m.group(1).replace("-", " ").title() if m else "Unknown"
            return {
                "title": data.get("text", "Unknown"),
                "company": company,
                "location": loc,
                "raw_description": description,
                "remote": remote,
            }
        except Exception:
            pass

    # HTML fallback
    html = _fetch(url)
    if not html:
        return _fallback(url)
    soup = _make_soup(html)
    title   = _text(soup, ".posting-headline h2") or _text(soup, "h2")
    company = _text(soup, ".main-header-text .company-name")
    location = _text(soup, ".location") or _text(soup, ".posting-category.location")
    desc_el = soup.select_one(".posting-description") or soup.select_one("main")
    description = desc_el.get_text("\n", strip=True)[:10000] if desc_el else ""
    if not company:
        m = re.search(r"lever\.co/([^/]+)", url)
        company = m.group(1).replace("-", " ").title() if m else "Unknown"
    return {"title": title or "Unknown", "company": company, "location": location or "",
            "raw_description": description}


# ---------------------------------------------------------------------------
# Ashby  (jobs.ashbyhq.com/company/uuid)
# ---------------------------------------------------------------------------

def _scrape_ashby(url: str) -> dict:
    # Ashby renders via React — try their public API first
    m = re.search(r"ashbyhq\.com/([^/]+)/([^/?]+)", url)
    if m:
        org, job_id = m.group(1), m.group(2)
        try:
            api_url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
            data = requests.post(api_url, json={"jobPostingId": job_id},
                                 headers={**HEADERS, "Content-Type": "application/json"},
                                 timeout=10).json()
            posting = data.get("jobPosting") or {}
            if posting:
                desc = BeautifulSoup(posting.get("descriptionHtml", ""), "html.parser")
                return {
                    "title": posting.get("title", "Unknown"),
                    "company": posting.get("organizationName", org.replace("-", " ").title()),
                    "location": posting.get("locationName", ""),
                    "raw_description": desc.get_text("\n", strip=True)[:10000],
                    "remote": posting.get("isRemote", False),
                }
        except Exception:
            pass

    # HTML fallback with Playwright
    html = _fetch_playwright(url) or _fetch(url) or ""
    soup = _make_soup(html)
    title = _text(soup, "h1")
    desc_el = soup.select_one("main") or soup.select_one("article")
    description = desc_el.get_text("\n", strip=True)[:10000] if desc_el else ""
    m2 = re.search(r"ashbyhq\.com/([^/]+)", url)
    company = m2.group(1).replace("-", " ").title() if m2 else "Unknown"
    return {"title": title or "Unknown", "company": company, "raw_description": description}


# ---------------------------------------------------------------------------
# Workday  (company.myworkdayjobs.com)
# ---------------------------------------------------------------------------

def _scrape_workday(url: str) -> dict:
    # Workday is fully JS-rendered — Playwright required
    html = _fetch_playwright(url)
    if not html:
        return _fallback(url)
    soup = _make_soup(html)
    title = (_text(soup, "[data-automation-id='jobPostingHeader']")
             or _text(soup, "h1"))
    location = (_text(soup, "[data-automation-id='locations']")
                or _text(soup, ".css-129m7dg"))
    desc_el = (soup.select_one("[data-automation-id='jobPostingDescription']")
               or soup.select_one("main"))
    description = desc_el.get_text("\n", strip=True)[:10000] if desc_el else ""
    host = urlparse(url).netloc
    company = host.split(".")[0].replace("-", " ").title()
    return {"title": title or "Unknown", "company": company, "location": location or "",
            "raw_description": description}


# ---------------------------------------------------------------------------
# Indeed  (indeed.com/viewjob?jk=... or indeed.com/jobs/...)
# ---------------------------------------------------------------------------

def _scrape_indeed(url: str) -> dict:
    """Scrape Indeed job pages using Playwright + cookies to bypass bot detection."""
    cookies = _load_indeed_cookies()
    html = _fetch_playwright_with_cookies(url, "indeed.com", cookies)
    if not html:
        return _fallback(url)
    soup = _make_soup(html)

    title = (
        _text(soup, 'h1[data-testid="jobsearch-JobInfoHeader-title"]')
        or _text(soup, ".jobsearch-JobInfoHeader-title")
        or _text(soup, "h1")
    )

    company = (
        _text(soup, '[data-testid="inlineHeader-companyName"] a')
        or _text(soup, '[data-testid="inlineHeader-companyName"]')
        or _text(soup, ".jobsearch-InlineCompanyRating a")
        or _text(soup, ".jobsearch-CompanyInfoWithoutHeaderImage a")
    )

    location = (
        _text(soup, '[data-testid="job-location"]')
        or _text(soup, ".jobsearch-JobInfoHeader-subtitle [data-testid]")
        or _text(soup, ".jobsearch-JobInfoHeader-subtitle")
    )
    remote = "remote" in (location or "").lower()

    desc_el = (
        soup.select_one('[data-testid="jobDescriptionText"]')
        or soup.select_one("#jobDescriptionText")
        or soup.select_one(".jobsearch-jobDescriptionText")
        or soup.select_one("main")
    )
    description = desc_el.get_text("\n", strip=True)[:10000] if desc_el else ""

    if not title or title == "Unknown":
        return _fallback(url)

    return {
        "title": title,
        "company": company or _company_from_url(url),
        "location": location or "",
        "raw_description": description,
        "remote": remote,
    }


def _load_indeed_cookies() -> list[dict]:
    """Load Indeed cookies from cookies.json and convert to Playwright format."""
    try:
        from pathlib import Path
        cookies_path = Path(__file__).parent.parent.parent / "cookies.json"
        if not cookies_path.exists():
            return []
        with open(cookies_path) as f:
            data = json.load(f)
        raw = data.get("indeed", "")
        if not raw:
            return []
        cookies = []
        for part in raw.split(";"):
            part = part.strip()
            if "=" in part:
                name, _, value = part.partition("=")
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".indeed.com",
                    "path": "/",
                })
        return cookies
    except Exception:
        return []


def _fetch_playwright_with_cookies(url: str, domain: str, cookies: list[dict]) -> str | None:
    """Fetch a page with Playwright, injecting cookies before navigation."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
                ),
            )
            if cookies:
                ctx.add_cookies(cookies)
            page = ctx.new_page()
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ZipRecruiter  (all URL patterns including /candidate/saved-jobs?lk=...)
# ---------------------------------------------------------------------------

def _scrape_ziprecruiter(url: str) -> dict:
    # ZipRecruiter blocks plain requests — Playwright handles bot detection
    html = _fetch_playwright(url) or ""
    if not html:
        return _fallback(url)
    soup = _make_soup(html)

    # JSON-LD is the most reliable — ZipRecruiter includes JobPosting schema on detail pages
    ld = _extract_json_ld(soup)
    if ld and ld.get("title"):
        loc_raw = ld.get("jobLocation") or {}
        if isinstance(loc_raw, list):
            loc_raw = loc_raw[0] if loc_raw else {}
        addr = loc_raw.get("address") or {}
        location = addr.get("addressLocality", "") or addr.get("addressRegion", "")
        company = (ld.get("hiringOrganization") or {}).get("name", "") or _company_from_url(url)
        desc_soup = BeautifulSoup(ld.get("description", ""), "html.parser")
        description = desc_soup.get_text("\n", strip=True)[:10000] or _best_description(soup)
        remote = "remote" in (location + " " + ld.get("jobLocationType", "")).lower()
        return {
            "title": ld["title"],
            "company": company,
            "location": location,
            "raw_description": description,
            "remote": remote,
        }

    # CSS selector fallback
    title = (
        _text(soup, "h2.title")
        or _text(soup, '[class*="job_title"]')
        or _text(soup, '[class*="jobTitle"]')
        or _text(soup, "h1")
    )
    company = (
        _text(soup, '[class*="hiring_company"]')
        or _text(soup, '[class*="company_name"]')
        or _text(soup, '[class*="companyName"]')
        or _company_from_url(url)
    )
    location = (
        _text(soup, '[class*="location"]')
        or _text(soup, '[class*="job_location"]')
    )
    remote = "remote" in (location or "").lower()
    desc_el = (
        soup.select_one("#job_desc")
        or soup.select_one('[class*="jobDescription"]')
        or soup.select_one('[class*="job_description"]')
        or soup.select_one("main")
    )
    description = desc_el.get_text("\n", strip=True)[:10000] if desc_el else _best_description(soup)

    if not title or title == "Unknown":
        return _fallback(url)

    return {
        "title": title,
        "company": company,
        "location": location or "",
        "raw_description": description,
        "remote": remote,
    }


# ---------------------------------------------------------------------------
# Generic fallback
# ---------------------------------------------------------------------------

def _scrape_generic(url: str) -> dict:
    html = _fetch(url)
    if not html or len(html) < 2000:
        html = _fetch_playwright(url) or html or ""
    return _parse_generic_html(html, url)


def _fallback(url: str) -> dict:
    html = _fetch_playwright(url) or _fetch(url) or ""
    return _parse_generic_html(html, url)


def _parse_generic_html(html: str, url: str) -> dict:
    soup = _make_soup(html)
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Try JSON-LD first
    ld = _extract_json_ld(soup)
    if ld and ld.get("title"):
        loc_raw = ld.get("jobLocation") or {}
        if isinstance(loc_raw, list):
            loc_raw = loc_raw[0] if loc_raw else {}
        location = (loc_raw.get("address") or {}).get("addressLocality", "")
        company  = (ld.get("hiringOrganization") or {}).get("name", "")
        desc_soup = BeautifulSoup(ld.get("description", ""), "html.parser")
        description = desc_soup.get_text("\n", strip=True)[:10000] or _best_description(soup)
        return {"title": ld["title"], "company": company or _company_from_url(url),
                "location": location, "raw_description": description}

    # Common selectors
    title_sel = ["h1[class*='title']", "h1[class*='job']", "h1[class*='position']", "h1"]
    title = next(
        (soup.select_one(s).get_text(strip=True)[:200]
         for s in title_sel if soup.select_one(s) and soup.select_one(s).get_text(strip=True)),
        "Unknown Title",
    )
    # Clean page-title suffixes
    page_title = soup.find("title")
    if page_title and title == "Unknown Title":
        raw = page_title.get_text(strip=True)
        title = re.split(r"\s+[-|–·]\s+", raw)[0].strip()[:200]

    company_sel = ["[class*='company']", "[class*='employer']", "[class*='organization']"]
    company = next(
        (soup.select_one(s).get_text(strip=True)[:100]
         for s in company_sel if soup.select_one(s) and soup.select_one(s).get_text(strip=True)),
        _company_from_url(url),
    )

    location_sel = ["[class*='location']", "[class*='address']", "[class*='city']"]
    location = next(
        (soup.select_one(s).get_text(strip=True)[:100]
         for s in location_sel if soup.select_one(s) and soup.select_one(s).get_text(strip=True)),
        "",
    )

    return {"title": title, "company": company, "location": location,
            "raw_description": _best_description(soup)}


def _best_description(soup: BeautifulSoup) -> str:
    for sel in ["#job-description", ".job-description", "[class*='description']",
                "[class*='content']", "article", "main"]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text("\n", strip=True)
            if len(text) > 300:
                return text[:10000]
    return soup.get_text("\n", strip=True)[:10000]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def _fetch_playwright(url: str) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(extra_http_headers={"Accept-Language": "en-US,en;q=0.9"})
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return None


def _make_soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def _text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""


def _extract_json_ld(soup: BeautifulSoup) -> dict | None:
    """Extract the first JobPosting schema from JSON-LD blocks."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict):
                if data.get("@type") == "JobPosting":
                    return data
                # Sometimes nested inside @graph
                for item in data.get("@graph", []):
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        return item
        except Exception:
            continue
    return None


def _company_from_url(url: str) -> str:
    host = urlparse(url).netloc
    parts = host.replace("www.", "").split(".")
    return parts[0].replace("-", " ").title() if parts else "Unknown"
