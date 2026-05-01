"""
Computes application pipeline metrics.

Returns an InsightReport with: funnel counts, response rate,
avg fit scores (responded vs. no-response), top missing skills,
and average days in pipeline.
"""

import sqlite3
from collections import Counter
from datetime import datetime

from app.db.database import get_all_applications, get_all_jobs
from app.models.models import InsightReport

RESPONDED = {"phone", "onsite", "offer"}
TERMINAL = {"offer", "rejected"}


def run(conn: sqlite3.Connection) -> InsightReport:
    applications = get_all_applications(conn)
    all_jobs = get_all_jobs(conn)
    report = InsightReport()

    status_counts: Counter = Counter(a.get("status", "saved") for a in applications)
    report.total_saved = status_counts.get("saved", 0)
    report.total_applied = status_counts.get("applied", 0)
    report.phone_screens = status_counts.get("phone", 0)
    report.onsites = status_counts.get("onsite", 0)
    report.offers = status_counts.get("offer", 0)
    report.rejections = status_counts.get("rejected", 0)

    total_responses = report.phone_screens + report.onsites + report.offers
    if report.total_applied > 0:
        report.response_rate = round(total_responses / report.total_applied * 100, 1)

    responded_scores = [
        a["fit_score"] for a in applications
        if a.get("status") in RESPONDED and a.get("fit_score") is not None
    ]
    no_response_scores = [
        a["fit_score"] for a in applications
        if a.get("status") == "applied" and a.get("fit_score") is not None
    ]
    report.avg_fit_responded = (
        round(sum(responded_scores) / len(responded_scores), 1) if responded_scores else 0.0
    )
    report.avg_fit_no_response = (
        round(sum(no_response_scores) / len(no_response_scores), 1) if no_response_scores else 0.0
    )

    rejected_ids = {a["job_id"] for a in applications if a.get("status") == "rejected"}
    missing_counter: Counter = Counter()
    for job in all_jobs:
        if job.get("id") in rejected_ids:
            missing = (job.get("fit_breakdown") or {}).get("missing_skills", [])
            missing_counter.update(missing)
    report.top_missing_skills = [s for s, _ in missing_counter.most_common(5)]

    pipeline_days = []
    for a in applications:
        if a.get("status") in TERMINAL and a.get("applied_at"):
            try:
                start = datetime.fromisoformat(a["applied_at"])
                end = datetime.fromisoformat(a.get("updated_at") or a["applied_at"])
                pipeline_days.append((end - start).days)
            except Exception:
                pass
    report.days_in_pipeline = (
        round(sum(pipeline_days) / len(pipeline_days), 1) if pipeline_days else 0.0
    )

    return report
