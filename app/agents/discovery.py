"""
Discovers new job postings automatically.

Auth sources (uses your Chrome login session — no password needed):
  - LinkedIn  job search
  - Indeed    job search

Free/public sources (no auth required):
  - Remotive      https://remotive.com/api/remote-jobs
  - RemoteOK      https://remoteok.com/api
  - We Work Remotely  RSS
  - Arbeitnow     https://www.arbeitnow.com/api/job-board-api

Flow: extract Chrome cookies → inject into Playwright → scrape search results
→ deduplicate against existing jobs → parse + score each new one.
"""

import re
import time
import sqlite3
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup

from app.db.database import get_or_create_profile, insert_job, get_job_by_id, delete_job
from app.agents.parser import run as parse_job
from app.agents.fit_scorer import run as score_job

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Titles containing any of these words are senior/leadership roles — not relevant for new-grad search
_SENIOR_RE = re.compile(
    r"\b(senior|sr\.?|principal|staff|lead|director|vp|"
    r"vice\s+president|head\s+of|manager|architect|distinguished|fellow)\b",
    re.I,
)

# Title must contain at least one of these to be a tech/software role
_TECH_TITLE_RE = re.compile(
    r"\b(software|engineer|developer|dev|programmer|backend|frontend|"
    r"full.?stack|fullstack|web|mobile|ios|android|ml|ai|devops|sre|"
    r"platform|infrastructure|api|cloud|python|javascript|"
    r"typescript|react|java|golang|rust|site\s+reliability)\b",
    re.I,
)

# Location strings that indicate non-US geography (even on remote jobs)
_NON_US_RE = re.compile(
    r"\b(germany|berlin|munich|hamburg|uk|united kingdom|london|england|"
    r"europe|european union|india|bangalore|mumbai|canada|toronto|vancouver|"
    r"australia|sydney|melbourne|france|paris|netherlands|amsterdam|poland|"
    r"warsaw|spain|madrid|brazil|mexico|colombia|singapore|japan|china|"
    r"korea|israel|ireland|sweden|norway|denmark|finland|switzerland|"
    r"austria|belgium|portugal|czechia|czech republic|romania|"
    r"latin america|south america|central america|apac|emea|worldwide\s+except\s+us|"
    r"turkey|türkiye|istanbul|ankara|saudi|riyadh|uae|dubai|abu\s+dhabi|"
    r"pakistan|karachi|lahore|nigeria|lagos|kenya|nairobi|egypt|cairo|"
    r"argentina|chile|peru|ukraine|kyiv|russia|moscow|philippines|manila|"
    r"indonesia|jakarta|vietnam|thailand|bangladesh|guatemala|costa rica|"
    r"italy|rome|milan|greece|athens|hungary|budapest|bulgaria|sofia|"
    r"croatia|serbia|belgrade|slovakia|lithuania|latvia|estonia|"
    r"new zealand|auckland|south africa|johannesburg|cape town|"
    r"malaysia|kuala lumpur|taiwan|taipei|hong kong|myanmar|cambodia|"
    r"nepal|sri lanka|morocco|tunisia|algeria|ghana|ethiopia|tanzania|"
    r"gibraltar|nicaragua|panama|honduras|el salvador|dominican republic|"
    r"lucknow|chennai|hyderabad|pune|delhi|kolkata|ahmedabad|jaipur)\b",
    re.I,
)

# Non-Latin scripts (Arabic, Chinese, Japanese, Korean, Cyrillic, Devanagari, etc.)
_NON_LATIN_RE = re.compile(
    r"[؀-ۿ一-鿿぀-ヿ가-힯"
    r"Ѐ-ӿऀ-ॿ฀-๿]"
)

# Absolute US livable wage floor — rejects roles clearly priced for non-US markets
_ABS_SALARY_FLOOR = 30_000


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

ALL_SOURCES = ["linkedin", "indeed", "remotive", "remoteok", "wwr", "arbeitnow"]

def run(conn: sqlite3.Connection, sources: list[str] | None = None) -> dict:
    """Discover new jobs. Returns summary dict.
    Pass sources=["linkedin"] to limit to a single source, or None for all.
    """
    active = {s.lower() for s in sources} if sources else set(ALL_SOURCES)

    profile = get_or_create_profile(conn)
    queries = _build_queries(profile)

    existing_urls = {
        r[0] for r in conn.execute("SELECT url FROM jobs WHERE url != ''").fetchall()
    }
    existing_title_co = {
        (r[0].lower().strip(), r[1].lower().strip())
        for r in conn.execute("SELECT title, company FROM jobs").fetchall()
    }

    pw_cookies = _get_playwright_cookies() if active & {"linkedin", "indeed"} else {}

    candidates: list[dict] = []
    sources_hit: list[str] = []

    for name, key, fetch_fn in [
        ("LinkedIn",         "linkedin",  lambda: _fetch_linkedin(queries, pw_cookies)),
        ("Indeed",           "indeed",    lambda: _fetch_indeed(queries, pw_cookies)),
        ("Remotive",         "remotive",  lambda: _fetch_remotive(queries)),
        ("RemoteOK",         "remoteok",  lambda: _fetch_remoteok(queries)),
        ("We Work Remotely", "wwr",       lambda: _fetch_wwr(queries)),
        ("Arbeitnow",        "arbeitnow", lambda: _fetch_arbeitnow(queries)),
    ]:
        if key not in active:
            continue
        try:
            jobs = fetch_fn()
            if jobs:
                candidates.extend(jobs)
                sources_hit.append(f"{name} ({len(jobs)})")
        except Exception as e:
            sources_hit.append(f"{name} (skipped: {type(e).__name__})")

    # Deduplicate against DB and within this batch by URL and (title, company)
    seen_urls: set[str] = set(existing_urls)
    seen_title_co: set[tuple] = set(existing_title_co)
    deduped: list[dict] = []
    for j in candidates:
        url = j.get("url", "")
        title_co = (j.get("title", "").lower().strip(), j.get("company", "").lower().strip())
        if not url:
            continue
        if url in seen_urls:
            continue
        if title_co[0] and title_co in seen_title_co:
            continue  # same job posted on multiple platforms
        seen_urls.add(url)
        seen_title_co.add(title_co)
        if _passes_filter(j, profile):
            deduped.append(j)

    inserted = 0
    for job in deduped:
        try:
            job_id = insert_job(conn, {
                "title":            job.get("title", "Unknown"),
                "company":          job.get("company", "Unknown"),
                "location":         job.get("location", ""),
                "url":              job["url"],
                "raw_description":  job.get("raw_description", ""),
                "skills":           [],
                "experience_years": None,
                "salary_min":       job.get("salary_min", 0),
                "salary_max":       job.get("salary_max", 0),
                "remote":           job.get("remote", False),
            })
            parse_job(conn, job_id)
            # Re-check after parsing — YOE is only known once description is parsed
            parsed = get_job_by_id(conn, job_id)
            if not _passes_filter(parsed, profile):
                delete_job(conn, job_id)
                continue
            score_job(conn, job_id)
            inserted += 1
        except Exception:
            pass

    return {"fetched": len(candidates), "new": inserted, "sources": sources_hit}


# ---------------------------------------------------------------------------
# Cookie extraction (Chrome → Playwright format)
# ---------------------------------------------------------------------------

def _get_playwright_cookies() -> dict[str, list[dict]]:
    """
    Loads cookies for LinkedIn and Indeed.
    Priority: cookies.json (manual) → browser_cookie3 (auto) → empty.
    """
    result: dict[str, list[dict]] = {"linkedin": [], "indeed": []}

    # 1. Manual cookie file — most reliable on macOS
    cookies_file = Path(__file__).parent.parent.parent / "cookies.json"
    if cookies_file.exists():
        try:
            import json as _json
            raw = _json.loads(cookies_file.read_text())
            for key in ("linkedin", "indeed"):
                cookie_str = raw.get(key, "")
                if cookie_str:
                    result[key] = _parse_cookie_string(cookie_str, key)
            if any(result.values()):
                return result
        except Exception:
            pass

    # 2. browser_cookie3 auto-extraction (often fails on macOS due to Keychain)
    try:
        import browser_cookie3

        def _to_pw(c) -> dict:
            return {
                "name":   c.name,
                "value":  c.value,
                "domain": c.domain if c.domain.startswith(".") else f".{c.domain}",
                "path":   c.path or "/",
                "secure": bool(c.secure),
                "httpOnly": False,
                "sameSite": "None",
            }

        for domain, key in [(".linkedin.com", "linkedin"), (".indeed.com", "indeed")]:
            raw = list(browser_cookie3.chrome(domain_name=domain))
            result[key] = [_to_pw(c) for c in raw if c.value]
    except Exception:
        pass
    return result


def _parse_cookie_string(cookie_str: str, site: str) -> list[dict]:
    """Parse a raw Cookie header string OR a single token value into Playwright format.
    For LinkedIn, a bare li_at token value is accepted directly.
    """
    domain_map = {"linkedin": ".linkedin.com", "indeed": ".indeed.com"}
    domain = domain_map.get(site, f".{site}.com")

    # If it looks like a single token (no = or ;), treat as li_at for LinkedIn
    if site == "linkedin" and "=" not in cookie_str and ";" not in cookie_str:
        return [{
            "name": "li_at",
            "value": cookie_str.strip(),
            "domain": domain,
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "None",
        }]

    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        name = name.strip()
        value = value.strip()
        if name and value:
            cookies.append({
                "name": name,
                "value": value,
                "domain": domain,
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "None",
            })
    return cookies


def _make_auth_session(cookies: list[dict]) -> requests.Session:
    """Build a requests.Session with the given cookies loaded."""
    s = requests.Session()
    s.headers.update(HEADERS)
    for c in cookies:
        s.cookies.set(c["name"], c["value"], domain=c["domain"])
    return s


# ---------------------------------------------------------------------------
# Auth sources
# ---------------------------------------------------------------------------

def _fetch_linkedin(queries: list[str], pw_cookies: dict) -> list[dict]:
    """
    Scrape LinkedIn job search using browser cookies + Playwright for JS rendering.
    Falls back to unauthenticated guest API if cookies unavailable.
    """
    li_cookies = pw_cookies.get("linkedin", [])

    results: list[dict] = []
    seen: set[str] = set()
    search_terms = _pick_terms(queries, 5)

    if li_cookies:
        # Use Playwright with injected cookies for full JS-rendered results
        try:
            results = _linkedin_playwright(search_terms, li_cookies, seen)
        except Exception:
            pass

    if not results:
        # Fallback: LinkedIn's guest job search API (public, no auth) — paginate up to 100 per term
        for term in search_terms:
            for start in range(0, 100, 25):
                try:
                    url = (
                        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                        f"?keywords={requests.utils.quote(term)}"
                        f"&location=Remote&f_E=1%2C2&f_WT=2&start={start}&count=25"
                    )
                    resp = requests.get(url, headers=HEADERS, timeout=15)
                    if resp.status_code != 200:
                        break
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Guest API returns <li><div data-entity-urn="urn:li:jobPosting:ID" class="job-search-card">
                    cards = soup.select("div[data-entity-urn]")
                    if not cards:
                        break  # no more results for this term
                    for card in cards:
                        job = _parse_linkedin_card(card)
                        if job and job["url"] not in seen:
                            seen.add(job["url"])
                            job["remote"] = True  # f_WT=2 guarantees remote; LI shows HQ location not "Remote"
                            results.append(job)
                    time.sleep(0.5)
                except Exception:
                    break

    return results


def _linkedin_playwright(terms: list[str], cookies: list[dict], seen: set) -> list[dict]:
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        for term in terms:
            try:
                encoded = requests.utils.quote(term)
                page.goto(
                    f"https://www.linkedin.com/jobs/search/?keywords={encoded}"
                    "&f_E=1%2C2&f_WT=2&location=Remote&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
                page.wait_for_timeout(3000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                for card in soup.select(
                    "li.scaffold-layout__list-item, "
                    "li.jobs-search-results__list-item, "
                    "div.job-card-container"
                ):
                    job = _parse_linkedin_card(card)
                    if job and job["url"] not in seen:
                        seen.add(job["url"])
                        results.append(job)
            except Exception:
                pass

        browser.close()
    return results


def _parse_linkedin_card(card) -> dict | None:
    # Try to extract job ID from various attributes
    job_id = (
        card.get("data-job-id")
        or card.get("data-entity-urn", "").split(":")[-1]
        or ""
    )
    title_el = (
        card.select_one(".job-card-list__title")
        or card.select_one(".base-search-card__title")
        or card.select_one("a[href*='/jobs/view/']")
    )
    company_el = (
        card.select_one(".job-card-container__company-name")
        or card.select_one(".base-search-card__subtitle")
        or card.select_one(".job-card-list__company-name")
    )
    location_el = (
        card.select_one(".job-card-container__metadata-item")
        or card.select_one(".job-search-card__location")
    )

    title   = title_el.get_text(strip=True) if title_el else ""
    company = company_el.get_text(strip=True) if company_el else ""
    location = location_el.get_text(strip=True) if location_el else ""

    # Build URL
    link_el = card.select_one("a[href*='/jobs/view/']")
    if link_el:
        href = link_el.get("href", "")
        m = re.search(r"/jobs/view/(\d+)", href)
        url = f"https://www.linkedin.com/jobs/view/{m.group(1)}/" if m else href
    elif job_id:
        url = f"https://www.linkedin.com/jobs/view/{job_id}/"
    else:
        return None

    if not title or not url:
        return None

    return {
        "title":    title,
        "company":  company,
        "location": location,
        "url":      url,
        "remote":   "remote" in location.lower(),
        "raw_description": "",
        "salary_min": 0,
        "salary_max": 0,
    }


def _fetch_indeed(queries: list[str], pw_cookies: dict) -> list[dict]:
    """Scrape Indeed — Playwright with cookies if available, RSS fallback otherwise."""
    indeed_cookies = pw_cookies.get("indeed", [])
    if indeed_cookies:
        results = _fetch_indeed_playwright(queries, indeed_cookies)
        if results:
            return results
    return _fetch_indeed_rss(queries)


def _fetch_indeed_playwright(queries: list[str], cookies: list[dict]) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
            ctx.add_cookies(cookies)
            page = ctx.new_page()

            for term in _pick_terms(queries, 3):
                try:
                    encoded = requests.utils.quote(term)
                    page.goto(
                        f"https://www.indeed.com/jobs?q={encoded}+entry+level"
                        "&l=Remote&limit=25&sort=date",
                        wait_until="domcontentloaded",
                        timeout=20000,
                    )
                    page.wait_for_timeout(2500)
                    html = page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    for card in soup.select("div[data-jk], td.resultContent"):
                        job_key = (
                            card.get("data-jk")
                            or (card.find_parent("[data-jk]") or {}).get("data-jk", "")
                        )
                        title_el   = card.select_one("h2.jobTitle span, [data-testid='jobTitle']")
                        company_el = card.select_one("[data-testid='company-name'], .companyName")
                        loc_el     = card.select_one("[data-testid='text-location'], .companyLocation")

                        title   = title_el.get_text(strip=True) if title_el else ""
                        company = company_el.get_text(strip=True) if company_el else ""
                        loc     = loc_el.get_text(strip=True) if loc_el else ""

                        if not title or not job_key:
                            continue
                        url = f"https://www.indeed.com/viewjob?jk={job_key}"
                        if url in seen:
                            continue
                        seen.add(url)
                        results.append({
                            "title":    title,
                            "company":  company,
                            "location": loc,
                            "url":      url,
                            "remote":   "remote" in loc.lower(),
                            "raw_description": "",
                            "salary_min": 0,
                            "salary_max": 0,
                        })
                except Exception:
                    pass

            browser.close()
    except Exception:
        pass
    return results


def _fetch_indeed_rss(queries: list[str]) -> list[dict]:
    """Public Indeed RSS feed — no auth required."""
    results: list[dict] = []
    seen: set[str] = set()
    for term in _pick_terms(queries, 3):
        try:
            resp = requests.get(
                "https://www.indeed.com/rss",
                params={"q": term + " entry level", "l": "Remote", "sort": "date", "limit": 25},
                headers=HEADERS, timeout=15,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            for item in root.iter("item"):
                title_el = item.find("title")
                link_el  = item.find("link")
                desc_el  = item.find("description")
                title = (title_el.text or "") if title_el is not None else ""
                url   = (link_el.text or "")  if link_el  is not None else ""
                desc  = BeautifulSoup((desc_el.text or ""), "html.parser").get_text("\n")[:10000] if desc_el is not None else ""
                if not url or url in seen:
                    continue
                seen.add(url)
                # RSS title format: "Job Title - Company Name"
                parts = title.rsplit(" - ", 1)
                job_title = parts[0].strip()
                company   = parts[1].strip() if len(parts) > 1 else ""
                results.append({
                    "title":           job_title,
                    "company":         company,
                    "location":        "Remote",
                    "url":             url,
                    "remote":          True,
                    "raw_description": desc,
                    "salary_min":      0,
                    "salary_max":      0,
                })
            time.sleep(0.5)
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# Free public sources
# ---------------------------------------------------------------------------

def _fetch_remotive(queries: list[str]) -> list[dict]:
    seen: set[str] = set()
    results: list[dict] = []
    for term in _pick_terms(queries, 3):
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": term, "limit": 50},
            headers=HEADERS, timeout=15,
        )
        resp.raise_for_status()
        for item in resp.json().get("jobs", []):
            url = item.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            desc = BeautifulSoup(item.get("description", ""), "html.parser").get_text("\n")[:10000]
            sal_min, sal_max = _parse_salary_range(item.get("salary", ""))
            results.append({
                "title":           item.get("title", ""),
                "company":         item.get("company_name", ""),
                "location":        item.get("candidate_required_location", "Remote"),
                "url":             url,
                "raw_description": desc,
                "remote":          True,
                "salary_min":      sal_min,
                "salary_max":      sal_max,
            })
        time.sleep(0.5)
    return results


def _fetch_remoteok(queries: list[str]) -> list[dict]:
    resp = requests.get(
        "https://remoteok.com/api",
        headers={**HEADERS, "Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and data:
        data = data[1:]

    keywords = {w for q in queries for w in q.lower().split()}
    results: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = (item.get("position") or "").lower()
        tags  = " ".join(item.get("tags") or []).lower()
        if not any(kw in title + " " + tags for kw in keywords):
            continue
        url = item.get("url") or ""
        if url and not url.startswith("http"):
            url = "https://remoteok.com" + url
        if not url:
            continue
        desc = BeautifulSoup(item.get("description") or "", "html.parser").get_text("\n")[:10000]
        results.append({
            "title":           item.get("position", ""),
            "company":         item.get("company", ""),
            "location":        "Remote",
            "url":             url,
            "raw_description": desc,
            "remote":          True,
            "salary_min":      int(item.get("salary_min") or 0),
            "salary_max":      int(item.get("salary_max") or 0),
        })
    return results


def _fetch_wwr(queries: list[str]) -> list[dict]:
    resp = requests.get(
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        headers=HEADERS, timeout=15,
    )
    resp.raise_for_status()
    keywords = {w for q in queries for w in q.lower().split() if len(w) > 3}
    results: list[dict] = []
    root = ET.fromstring(resp.content)
    for item in root.iter("item"):
        title_el   = item.find("title")
        link_el    = item.find("link")
        desc_el    = item.find("description")
        title   = title_el.text if title_el is not None else ""
        url     = link_el.text  if link_el  is not None else ""
        desc    = BeautifulSoup(desc_el.text or "", "html.parser").get_text("\n")[:10000] if desc_el is not None else ""
        if not url or not any(kw in title.lower() for kw in keywords):
            continue
        # Parse "Company: Title" format
        parts = title.split(":", 1)
        company, job_title = (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else ("", title)
        results.append({
            "title":           job_title,
            "company":         company,
            "location":        "Remote",
            "url":             url,
            "raw_description": desc,
            "remote":          True,
            "salary_min":      0,
            "salary_max":      0,
        })
    return results


def _fetch_arbeitnow(queries: list[str]) -> list[dict]:
    resp = requests.get(
        "https://www.arbeitnow.com/api/job-board-api",
        params={"remote": "true"},
        headers=HEADERS, timeout=15,
    )
    resp.raise_for_status()
    keywords = {w for q in queries for w in q.lower().split() if len(w) > 3}
    results: list[dict] = []
    for item in resp.json().get("data", []):
        title = (item.get("title") or "").lower()
        url   = item.get("url") or ""
        if not url or not any(kw in title for kw in keywords):
            continue
        desc = BeautifulSoup(item.get("description") or "", "html.parser").get_text("\n")[:10000]
        results.append({
            "title":           item.get("title", ""),
            "company":         item.get("company_name", ""),
            "location":        item.get("location", ""),
            "url":             url,
            "raw_description": desc,
            "remote":          bool(item.get("remote")),
            "salary_min":      0,
            "salary_max":      0,
        })
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_queries(profile: dict) -> list[str]:
    roles = profile.get("preferred_roles") or []
    base = [r.lower() for r in roles if 1 <= len(r.split()) <= 4]
    for fallback in [
        "software engineer", "software developer", "full stack developer",
        "backend engineer", "frontend engineer", "full stack engineer",
    ]:
        if fallback not in base:
            base.append(fallback)
    return base[:10]


def _pick_terms(queries: list[str], n: int) -> list[str]:
    priority_keywords = {"software engineer", "software developer", "full stack", "backend", "frontend"}
    priority = [q for q in queries if any(kw in q for kw in priority_keywords)]
    return (priority or queries)[:n]


def _parse_salary_range(s: str) -> tuple[int, int]:
    """Parse a salary string like '$80k - $120k' into (min, max)."""
    if not s:
        return 0, 0
    # Range with k: 80k - 120k or $80k-$120k
    m = re.search(r"\$?\s*(\d+)\s*[kK]\s*[-–]+\s*\$?\s*(\d+)\s*[kK]", s, re.I)
    if m:
        return int(m.group(1)) * 1000, int(m.group(2)) * 1000
    # Range with full numbers: 80,000 - 120,000
    m = re.search(r"(\d{4,})\s*[-–]+\s*(\d{4,})", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Single k value
    m = re.search(r"\$?\s*(\d+)\s*[kK]", s, re.I)
    if m:
        v = int(m.group(1)) * 1000
        return v, v
    # Single full number
    m = re.search(r"\$?\s*(\d{4,})", s)
    if m:
        v = int(m.group(1))
        return v, v
    return 0, 0


def _passes_filter(job: dict, profile: dict) -> bool:
    """Return False if the job doesn't match profile preferences or seniority requirements."""
    title = job.get("title") or ""
    job_loc = (job.get("location") or "").lower()

    # Must be a tech/software role
    if not _TECH_TITLE_RE.search(title):
        return False

    # Senior/leadership title — not relevant for entry-level search
    if _SENIOR_RE.search(title):
        return False

    # Non-Latin script in title or company — indicates non-English posting
    company = job.get("company") or ""
    if _NON_LATIN_RE.search(title) or _NON_LATIN_RE.search(company):
        return False

    # Reject if location explicitly names a non-US country (even on "remote" jobs)
    if _NON_US_RE.search(job_loc):
        return False

    # Also check title for embedded location hints (e.g. "Engineer (Brazil)", "Developer - LATAM")
    if _NON_US_RE.search(title):
        return False

    # Location / remote check against profile preferences
    locs = [l.lower().strip() for l in (profile.get("preferred_locations") or [])]
    wants_remote = any(l in ("remote", "anywhere", "remote us", "us remote") for l in locs)

    if wants_remote:
        is_hybrid = job.get("hybrid") is True
        # Hybrid overrides a forced remote=True (e.g. from LinkedIn search) — must pass location check
        job_remote = job.get("remote", False) and not is_hybrid
        is_remote_loc = "remote" in job_loc or "anywhere" in job_loc

        if job_remote or is_remote_loc:
            pass  # fully remote — ok
        elif not job_loc:
            pass  # unknown location — allow through
        else:
            # Hybrid or on-site: only ok if it matches a preferred location (Utah)
            other_locs = [l for l in locs if l not in ("remote", "anywhere", "remote us", "us remote")]
            if other_locs and any(loc in job_loc for loc in other_locs):
                pass  # hybrid/onsite in Utah — ok
            else:
                return False  # hybrid/onsite outside preferred locations

    # LLM relevance check — only reject when Ollama explicitly marked it false
    if job.get("relevant") is False:
        return False

    # YOE requirement — reject if explicitly more than 1 year required; allow if unspecified
    yoe = job.get("experience_years")
    if yoe is not None and yoe > 1:
        return False

    # Salary floor — reject if clearly below US livable wage or below profile minimum
    min_salary = profile.get("min_salary") or 0
    sal_max = job.get("salary_max") or 0
    if sal_max > 0 and sal_max < _ABS_SALARY_FLOOR:
        return False
    if min_salary and sal_max > 0 and sal_max < min_salary:
        return False

    return True


def _filter_reason(job: dict, profile: dict) -> str:
    """Human-readable explanation of why a job was filtered out."""
    title = job.get("title") or ""
    job_loc = (job.get("location") or "")

    if not _TECH_TITLE_RE.search(title):
        return f"Not a tech/software role — \"{title}\" doesn't match any software engineering keywords."

    if job.get("relevant") is False:
        return f"Not a relevant role — \"{title}\" was classified as data engineering, ML research, or another non-SWE specialization."

    if _SENIOR_RE.search(title):
        return (
            f"Senior/leadership role — \"{title}\" is above entry-level. "
            "Remove the seniority keyword from the title if you still want to track it."
        )

    if _NON_US_RE.search(job_loc.lower()):
        return f"Non-US location — \"{job_loc}\" is outside your preferred regions."

    locs = [l.lower().strip() for l in (profile.get("preferred_locations") or [])]
    wants_remote = any(l in ("remote", "anywhere", "remote us", "us remote") for l in locs)
    if wants_remote and not job.get("remote") and job_loc:
        pref = ", ".join(profile.get("preferred_locations") or [])
        return f"Location mismatch — \"{job_loc}\" doesn't match your preferred locations ({pref})."

    yoe = job.get("experience_years")
    if yoe is not None and yoe > 1:
        return f"Experience requirement too high — posting requires {yoe}+ years (your threshold is 1)."

    min_salary = profile.get("min_salary") or 0
    sal_max = job.get("salary_max") or 0
    if min_salary and sal_max > 0 and sal_max < min_salary:
        return f"Salary too low — max ${sal_max:,} is below your minimum ${min_salary:,}."

    return "Doesn't match your profile filters."
