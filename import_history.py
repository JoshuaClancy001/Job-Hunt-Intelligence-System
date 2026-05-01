#!/usr/bin/env python3
"""
Imports job application history from spreadsheet data.

Scrapes each URL for description/skills, then overrides company/title/salary
with the verified spreadsheet values. Creates applications with correct
status, submission dates, and rejection reasons.
"""
import sys
from app.db.database import get_connection, insert_job, insert_application
from app.scraper.scraper import scrape_url
from app.agents.parser import run as parse_job
from app.agents.fit_scorer import run as score_job

JOBS = [
    {"company": "Valon", "title": "Software Engineer", "status": "applied",
     "salary_min": 170000, "salary_max": 200000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4366533102/", "rejection_reason": ""},
    {"company": "Crossing Hurdles", "title": "Backend Engineer", "status": "applied",
     "salary_min": 70, "salary_max": 150, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4385253267/", "rejection_reason": ""},
    {"company": "Fuze Health", "title": "Graduate Software Engineer", "status": "applied",
     "salary_min": 75000, "salary_max": 95000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4394792247/", "rejection_reason": ""},
    {"company": "Voltus", "title": "Software Engineer", "status": "rejected",
     "salary_min": 110000, "salary_max": 140000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4390672806/", "rejection_reason": "Not a good fit"},
    {"company": "Honeywell", "title": "Software Engineer", "status": "rejected",
     "salary_min": 68000, "salary_max": 126000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4293208199/", "rejection_reason": "Filled internally"},
    {"company": "Rate", "title": "Software Engineer", "status": "applied",
     "salary_min": 100000, "salary_max": 100000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4382484258/", "rejection_reason": ""},
    {"company": "Vibefoundery.ai", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4397314273/", "rejection_reason": ""},
    {"company": "Hue", "title": "Software Engineer Intern", "status": "applied",
     "salary_min": 73000, "salary_max": 94000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4383055507/", "rejection_reason": ""},
    {"company": "Seesaw Learning", "title": "Full Stack Engineer", "status": "applied",
     "salary_min": 170000, "salary_max": 200000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4394681215/", "rejection_reason": ""},
    {"company": "Anrok", "title": "Software Engineer", "status": "rejected",
     "salary_min": 165000, "salary_max": 250000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4384560707/", "rejection_reason": "Filled internally"},
    {"company": "Bloomlogic", "title": "Full Stack Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4347034149/", "rejection_reason": ""},
    {"company": "Affirm", "title": "Backend Engineer", "status": "applied",
     "salary_min": 115000, "salary_max": 155000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4396341384/", "rejection_reason": ""},
    {"company": "Affirm", "title": "Full Stack Engineer", "status": "applied",
     "salary_min": 115000, "salary_max": 155000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4397612127/", "rejection_reason": ""},
    {"company": "pmtBox", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4386959288/", "rejection_reason": ""},
    {"company": "Great Value Hiring", "title": "Software Engineer Specialist", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4393071905/", "rejection_reason": ""},
    {"company": "Adobe", "title": "Software Development Engineer", "status": "applied",
     "salary_min": 93000, "salary_max": 180000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4365919705/", "rejection_reason": ""},
    {"company": "Figma", "title": "Software Engineer", "status": "applied",
     "salary_min": 150000, "salary_max": 375000, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4320296324/", "rejection_reason": ""},
    {"company": "Nice", "title": "Software Engineer AI Coding", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4388578745/", "rejection_reason": ""},
    {"company": "Joveo AI", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4403832157/", "rejection_reason": ""},
    {"company": "AutoDesk", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4403650881/", "rejection_reason": ""},
    {"company": "Trimble", "title": "Software Engineer", "status": "applied",
     "salary_min": 75000, "salary_max": 100000, "applied_at": "2026-04-21",
     "url": "https://trimble.eightfold.ai/careers/job/171840244462?microsite=trimble.com&domain=trimble.com&src=LinkedIN",
     "rejection_reason": ""},
    {"company": "Cotiviti", "title": "Associate Software Engineer", "status": "applied",
     "salary_min": 75000, "salary_max": 100000, "applied_at": "2026-04-21",
     "url": "https://careers-cotiviti.icims.com/jobs/18785/associate-software-engineer/job",
     "rejection_reason": ""},
    {"company": "Concentrate AI", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-21",
     "url": "https://www.linkedin.com/jobs/view/4404884492/", "rejection_reason": ""},
    {"company": "Funnel Leasing", "title": "Software Engineer", "status": "rejected",
     "salary_min": 80000, "salary_max": 90000, "applied_at": "2026-04-21",
     "url": "https://www.linkedin.com/jobs/view/4389755755/", "rejection_reason": "Not a good fit"},
    {"company": "Nucleus Security", "title": "Software Engineer", "status": "applied",
     "salary_min": 80000, "salary_max": 110000, "applied_at": "2026-04-21",
     "url": "https://nucleussecurity.applytojob.com/apply/G11OrHQOkV/Software-Engineer",
     "rejection_reason": ""},
    {"company": "RK InfoTech LLC", "title": "Software Engineer", "status": "applied",
     "salary_min": 70000, "salary_max": 110000, "applied_at": "2026-04-25",
     "url": "https://www.linkedin.com/jobs/view/4374000978/", "rejection_reason": ""},
    {"company": "Stealth AI", "title": "Backend Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-26",
     "url": "https://www.linkedin.com/jobs/view/4403205387/", "rejection_reason": ""},
    {"company": "Elios", "title": "Full Stack Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4391882535/", "rejection_reason": ""},
    {"company": "OP Consulting Group", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": None,
     "url": "https://www.linkedin.com/jobs/view/4400441786/", "rejection_reason": ""},
    {"company": "Files", "title": "Backend Engineer", "status": "rejected",
     "salary_min": 110000, "salary_max": 250000, "applied_at": "2026-04-26",
     "url": "https://www.linkedin.com/jobs/view/4405268055/", "rejection_reason": "Not a good fit"},
    {"company": "Intellect Group", "title": "Software Engineer", "status": "applied",
     "salary_min": 160000, "salary_max": 200000, "applied_at": "2026-04-26",
     "url": "https://www.linkedin.com/jobs/view/4405429516/", "rejection_reason": ""},
    {"company": "Green Line", "title": "Entry-Level Developer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-26",
     "url": "https://www.linkedin.com/jobs/view/4385283620/", "rejection_reason": ""},
    {"company": "Sunwest Mortgage", "title": "Software Engineer", "status": "phone",
     "salary_min": 100000, "salary_max": 200000, "applied_at": "2026-04-26",
     "url": "https://www.linkedin.com/jobs/view/4404099771/", "rejection_reason": ""},
    {"company": "Grit", "title": "Full Stack Developer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-26",
     "url": "https://www.indeed.com/viewjob?from=app-tracker-saved-appcard&hl=en&jk=8b879eaa84aa34f7&tk=1jn6gku6bjlp9800",
     "rejection_reason": ""},
    {"company": "Kalos Health", "title": "Software Engineer", "status": "applied",
     "salary_min": 130000, "salary_max": 170000, "applied_at": "2026-04-28",
     "url": "https://www.indeed.com/viewjob?from=app-tracker-post_apply-appcard&hl=en&jk=68393b0acca7ed81&tk=1jnb84sls22vb000",
     "rejection_reason": ""},
    {"company": "Roboflow", "title": "Full Stack Engineer", "status": "applied",
     "salary_min": 165000, "salary_max": 195000, "applied_at": "2026-04-28",
     "url": "https://www.linkedin.com/jobs/view/4318514326/", "rejection_reason": ""},
    {"company": "Aleph", "title": "Software Engineer", "status": "applied",
     "salary_min": 75000, "salary_max": 315000, "applied_at": "2026-04-28",
     "url": "https://www.linkedin.com/jobs/view/4317706166/", "rejection_reason": ""},
    {"company": "Jonas Software", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-28",
     "url": "https://www.linkedin.com/jobs/view/4391757105/", "rejection_reason": ""},
    {"company": "Better Body", "title": "Full Stack Developer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-28",
     "url": "https://www.indeed.com/viewjob?from=app-tracker-saved-appcard&hl=en&jk=379be7d708fcbe96&tk=1jnbcqjgukndc800",
     "rejection_reason": ""},
    {"company": "CyberCoders", "title": "Software Engineer", "status": "applied",
     "salary_min": 90000, "salary_max": 140000, "applied_at": "2026-04-29",
     "url": "https://www.linkedin.com/jobs/view/4404112924/", "rejection_reason": ""},
    {"company": "Atano", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-29",
     "url": "https://www.linkedin.com/jobs/view/4405430435/", "rejection_reason": ""},
    {"company": "HartleyCo", "title": "Founding Engineer", "status": "applied",
     "salary_min": 100000, "salary_max": 120000, "applied_at": "2026-04-29",
     "url": "https://www.linkedin.com/jobs/view/4405536984/", "rejection_reason": ""},
    {"company": "Trade Cafe", "title": "Junior Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-29",
     "url": "https://www.linkedin.com/jobs/view/4402529936/", "rejection_reason": ""},
    {"company": "Tree Top Staffing", "title": "Software Developer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-29",
     "url": "https://www.linkedin.com/jobs/view/4407139191/", "rejection_reason": ""},
    {"company": "Hilo Aviation", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-29",
     "url": "https://www.linkedin.com/jobs/view/4407458411/", "rejection_reason": ""},
    {"company": "Helic and Co", "title": "Junior Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-29",
     "url": "https://www.linkedin.com/jobs/view/4408296192/", "rejection_reason": ""},
    {"company": "InterProse", "title": "AI Engineer", "status": "applied",
     "salary_min": 85000, "salary_max": 110000, "applied_at": "2026-04-30",
     "url": "https://www.indeed.com/viewjob?from=app-tracker-post_apply-appcard&hl=en&jk=4cae0cd311b404d9&tk=1jng72db7ijre800",
     "rejection_reason": ""},
    {"company": "KBR", "title": "Junior Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-30",
     "url": "https://kbr.wd5.myworkdayjobs.com/en-US/KBR_Careers/job/Junior-Software-Engineer_R2122447",
     "rejection_reason": ""},
    {"company": "Paylocity", "title": "Implementation Software Engineer", "status": "applied",
     "salary_min": 80000, "salary_max": 110000, "applied_at": "2026-04-30",
     "url": "https://2000recruiting.paylocity.com/Recruiting/Jobs/Details/44457", "rejection_reason": ""},
    {"company": "Mixpanel", "title": "Software Engineer", "status": "applied",
     "salary_min": 0, "salary_max": 0, "applied_at": "2026-04-30",
     "url": "https://job-boards.greenhouse.io/embed/job_app?for=mixpanel&gh_src=beca423f1&source=LinkedIn&token=7773373",
     "rejection_reason": ""},
]


def main():
    conn = get_connection()

    existing = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    if existing > 0:
        print(f"Clearing {existing} existing job(s)...")
        conn.execute("DELETE FROM jobs")
        conn.commit()

    print(f"Scraping and importing {len(JOBS)} jobs...\n")
    ok = failed = 0

    for i, entry in enumerate(JOBS, 1):
        company = entry["company"]
        title = entry["title"]
        print(f"[{i:2d}/{len(JOBS)}] {company} — {title}")

        # Scrape for description and skills
        try:
            scraped = scrape_url(entry["url"])
            description = scraped.get("raw_description", "")
            location = scraped.get("location", "")
            remote = scraped.get("remote", False)
            print(f"         scraped {len(description)} chars")
        except Exception as e:
            description = ""
            location = ""
            remote = False
            print(f"         scrape failed: {e}")

        # Salary: prefer spreadsheet values, fall back to scraped
        sal_min = entry.get("salary_min") or scraped.get("salary_min", 0) if 'scraped' in dir() else entry.get("salary_min", 0)
        sal_max = entry.get("salary_max") or scraped.get("salary_max", 0) if 'scraped' in dir() else entry.get("salary_max", 0)

        job_id = insert_job(conn, {
            "title": title,
            "company": company,
            "location": location,
            "url": entry["url"],
            "raw_description": description,
            "skills": [],
            "experience_years": 0,
            "salary_min": sal_min,
            "salary_max": sal_max,
            "remote": remote,
        })

        # Parse description for skills
        try:
            parse_job(conn, job_id)
        except Exception as e:
            print(f"         parse warning: {e}")

        # Score against profile
        try:
            score_job(conn, job_id)
        except Exception as e:
            print(f"         score warning: {e}")

        insert_application(conn, {
            "job_id": job_id,
            "status": entry["status"],
            "applied_at": entry.get("applied_at"),
            "notes": "",
            "cover_letter": "",
            "resume_bullets": [],
            "rejection_reason": entry.get("rejection_reason", ""),
        })

        ok += 1

    print(f"\n{'─'*50}")
    print(f"Done. {ok} imported, {failed} skipped.")


if __name__ == "__main__":
    main()
