#!/usr/bin/env python3
"""
Job Hunt Intelligence System — CLI

Commands:
  demo        Load sample data and run the full pipeline
  scrape      Scrape a job posting URL
  add         Manually add a job (paste description, no URL needed)
  analyze     Parse and score all jobs
  apply       Track or update an application status
  insights    Show application funnel and metrics
  generate    Generate a cover letter or resume bullets
  profile     Show or load the candidate profile
  list        List all jobs in the database
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.db.database import (
    get_connection, get_all_jobs, get_job_by_id, get_or_create_profile,
    save_profile, get_all_applications, update_application_status,
    insert_application, get_application_for_job,
)

app = typer.Typer(
    name="jobs",
    help="Job Hunt Intelligence System — local-first job tracking with AI scoring.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

PROFILE_JSON = Path(__file__).parent / "profile.json"


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

@app.command()
def demo():
    """Load sample jobs, run parser + fit scorer, and display results."""
    from app.services.demo import run as load_demo
    from app.agents.parser import run as parse_job
    from app.agents.fit_scorer import score_all

    conn = get_connection()
    console.print(Panel.fit(
        "[bold cyan]Job Hunt Intelligence System[/bold cyan]\n[dim]Loading demo data...[/dim]",
        border_style="cyan",
    ))

    result = load_demo(conn)
    if result["status"] == "already_loaded":
        console.print("[yellow]Demo data already loaded — running analysis on existing data.[/yellow]")
    else:
        console.print(
            f"[green]✓[/green] Loaded [bold]{result['jobs_inserted']}[/bold] sample jobs "
            f"for profile [bold]{result['profile']}[/bold]"
        )

    console.print("\n[bold]Step 1:[/bold] Parsing job descriptions...")
    jobs = get_all_jobs(conn)
    parsed = sum(1 for j in jobs if not j.get("parsed_at") and (parse_job(conn, j["id"]) or True))
    console.print(f"  [green]✓[/green] Parsed {parsed} jobs")

    console.print("[bold]Step 2:[/bold] Scoring job fit...")
    scores = score_all(conn)
    console.print(f"  [green]✓[/green] Scored {len(scores)} jobs\n")

    _print_jobs_table(conn)

    console.print("\n[dim]Next steps:[/dim]")
    console.print("[dim]  python cli.py insights                              — application funnel[/dim]")
    console.print("[dim]  python cli.py generate --job-id 1 --type both       — cover letter + bullets[/dim]")
    console.print("[dim]  python cli.py apply --job-id 3 --status applied     — track an application[/dim]")


# ---------------------------------------------------------------------------
# scrape
# ---------------------------------------------------------------------------

@app.command()
def scrape(url: str = typer.Option(..., "--url", "-u", help="Job posting URL")):
    """Scrape a job posting URL, parse it, and score it."""
    from app.scraper.scraper import scrape_url
    from app.agents.parser import run as parse_job
    from app.agents.fit_scorer import run as score_job
    from app.db.database import insert_job

    conn = get_connection()
    console.print(f"[bold]Scraping:[/bold] {url}")

    with console.status("Fetching page..."):
        job_data = scrape_url(url)

    job_id = insert_job(conn, job_data)
    console.print(
        f"[green]✓ Saved[/green] job id={job_id}: "
        f"[bold]{job_data['title']}[/bold] at [bold]{job_data['company']}[/bold]"
    )

    with console.status("Parsing..."):
        parse_job(conn, job_id)

    with console.status("Scoring..."):
        score, breakdown = score_job(conn, job_id)

    _print_job_detail(conn, job_id)
    console.print(f"\n[bold]Fit score:[/bold] {_score_badge(score)}")
    if breakdown.get("notes"):
        console.print(f"[dim]{breakdown['notes']}[/dim]")


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

@app.command()
def analyze():
    """Parse and score all jobs in the database."""
    from app.agents.parser import parse_all
    from app.agents.fit_scorer import score_all

    conn = get_connection()
    with console.status("Parsing unparsed jobs..."):
        parse_all(conn)
    with console.status("Scoring all jobs..."):
        scores = score_all(conn)

    console.print(f"[green]✓[/green] Scored [bold]{len(scores)}[/bold] jobs\n")
    _print_jobs_table(conn)


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

@app.command()
def apply(
    job_id: int = typer.Option(..., "--job-id", help="Job ID to track"),
    status: str = typer.Option("applied", "--status", "-s",
                               help="saved|applied|phone|onsite|offer|rejected"),
    notes: str = typer.Option("", "--notes", "-n", help="Optional notes"),
):
    """Track or update an application status for a job."""
    valid = {"saved", "applied", "phone", "onsite", "offer", "rejected"}
    if status not in valid:
        console.print(f"[red]Invalid status.[/red] Choose from: {', '.join(sorted(valid))}")
        raise typer.Exit(1)

    conn = get_connection()
    job = get_job_by_id(conn, job_id)
    if not job:
        console.print(f"[red]Job id={job_id} not found.[/red]")
        raise typer.Exit(1)

    existing = get_application_for_job(conn, job_id)
    if existing:
        update_application_status(conn, existing["id"], status, notes)
        console.print(
            f"[green]✓ Updated[/green] [bold]{job['title']}[/bold] @ {job['company']} "
            f"→ [bold]{status}[/bold]"
        )
    else:
        applied_at = datetime.now().isoformat() if status == "applied" else None
        insert_application(conn, {
            "job_id": job_id, "status": status, "applied_at": applied_at,
            "notes": notes, "cover_letter": "", "resume_bullets": [],
        })
        console.print(
            f"[green]✓ Tracked[/green] [bold]{job['title']}[/bold] @ {job['company']} "
            f"— status: [bold]{status}[/bold]"
        )


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------

@app.command()
def insights():
    """Show application funnel metrics."""
    from app.agents.insights import run as compute_insights

    conn = get_connection()
    report = compute_insights(conn)

    # Funnel
    funnel = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    funnel.add_column("Stage", style="bold", width=14)
    funnel.add_column("Count", justify="right", width=6)
    funnel.add_column("Bar")

    stages = [
        ("Saved",        report.total_saved,    "dim"),
        ("Applied",      report.total_applied,  "blue"),
        ("Phone Screen", report.phone_screens,  "cyan"),
        ("Onsite",       report.onsites,        "yellow"),
        ("Offer",        report.offers,         "green"),
        ("Rejected",     report.rejections,     "red"),
    ]
    max_val = max((s[1] for s in stages), default=1) or 1
    for label, count, color in stages:
        bar = f"[{color}]{'█' * int(count / max_val * 20)}[/{color}]"
        funnel.add_row(label, str(count), bar)

    console.print(Panel(funnel, title="[bold]Application Funnel[/bold]", border_style="cyan"))

    # Key metrics
    metrics = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    metrics.add_column("Metric", style="bold", width=30)
    metrics.add_column("Value", justify="right")

    rate_color = "green" if report.response_rate > 20 else "yellow"
    metrics.add_row("Response rate", f"[{rate_color}]{report.response_rate}%[/{rate_color}]")
    metrics.add_row("Avg fit score (responded)", f"[cyan]{report.avg_fit_responded}[/cyan]")
    metrics.add_row("Avg fit score (no response)", f"[dim]{report.avg_fit_no_response}[/dim]")
    metrics.add_row("Avg days in pipeline", str(report.days_in_pipeline))

    console.print(Panel(metrics, title="[bold]Key Metrics[/bold]", border_style="blue"))

    if report.top_missing_skills:
        body = "[yellow]" + "\n".join(f"  • {s}" for s in report.top_missing_skills) + "[/yellow]"
        console.print(Panel(body, title="[bold]Top Missing Skills (from rejected jobs)[/bold]",
                            border_style="yellow"))


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

@app.command()
def generate(
    job_id: int = typer.Option(..., "--job-id", help="Job ID"),
    content_type: str = typer.Option("cover-letter", "--type", "-t",
                                     help="cover-letter | resume-bullets | both"),
):
    """Generate a cover letter and/or resume bullets (Ollama or template)."""
    from app.agents.writer import run as generate_content

    conn = get_connection()
    job = get_job_by_id(conn, job_id)
    if not job:
        console.print(f"[red]Job id={job_id} not found.[/red]")
        raise typer.Exit(1)

    console.print(f"Generating [bold]{content_type}[/bold] for "
                  f"[cyan]{job['title']}[/cyan] @ {job['company']}\n")

    with console.status("Generating (using Ollama if available, otherwise template)..."):
        result = generate_content(conn, job_id, content_type)

    source = "[green]Ollama AI[/green]" if result.source == "ollama" else "[yellow]Template[/yellow]"
    console.print(f"[dim]Source:[/dim] {source}\n")

    if result.cover_letter:
        console.print(Panel(result.cover_letter, title="[bold]Cover Letter[/bold]",
                            border_style="green"))

    if result.resume_bullets:
        body = "\n".join(f"  • {b}" for b in result.resume_bullets)
        console.print(Panel(body, title="[bold]Resume Bullet Points[/bold]",
                            border_style="blue"))


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------

@app.command()
def profile(
    load: bool = typer.Option(False, "--load", "-l", help="Load from profile.json"),
):
    """Show or reload the candidate profile."""
    conn = get_connection()

    if load:
        if not PROFILE_JSON.exists():
            console.print(f"[red]profile.json not found at {PROFILE_JSON}[/red]")
            raise typer.Exit(1)
        with open(PROFILE_JSON) as f:
            data = json.load(f)
        save_profile(conn, data)
        console.print("[green]✓ Profile loaded from profile.json[/green]\n")

    p = get_or_create_profile(conn)
    if not p.get("name"):
        console.print(
            "[yellow]No profile configured yet.[/yellow]\n"
            f"Edit [bold]{PROFILE_JSON}[/bold] then run [bold]python cli.py profile --load[/bold]"
        )
        return

    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column("Field", style="bold", width=20)
    t.add_column("Value")
    t.add_row("Name", p.get("name", ""))
    t.add_row("Experience", f"{p.get('experience_years', 0)} years")
    t.add_row("Skills", ", ".join(p.get("skills", [])))
    t.add_row("Preferred roles", ", ".join(p.get("preferred_roles", [])))
    t.add_row("Locations", ", ".join(p.get("preferred_locations", [])))
    t.add_row("Min salary", f"${p.get('min_salary', 0):,}")
    t.add_row("Summary", p.get("summary", ""))
    console.print(Panel(t, title="[bold]Candidate Profile[/bold]", border_style="cyan"))


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_jobs_table(conn) -> None:
    jobs = get_all_jobs(conn)
    if not jobs:
        console.print("[yellow]No jobs in database.[/yellow]")
        return

    table = Table(title="Job Postings", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("ID", width=4, justify="right")
    table.add_column("Title", width=28)
    table.add_column("Company", width=14)
    table.add_column("Loc", width=10)
    table.add_column("Rem", width=4, justify="center")
    table.add_column("Exp", width=4, justify="right")
    table.add_column("Salary", width=14, justify="right")
    table.add_column("Score", width=8, justify="right")
    table.add_column("Skills", width=30)

    for job in jobs:
        skills = ", ".join((job.get("skills") or [])[:4])
        if len(job.get("skills") or []) > 4:
            skills += "…"
        table.add_row(
            str(job["id"]),
            (job.get("title") or "")[:28],
            (job.get("company") or "")[:14],
            (job.get("location") or "")[:10],
            "[green]✓[/green]" if job.get("remote") else "[dim]✗[/dim]",
            str(int(job.get("experience_years") or 0)),
            _fmt_salary(job.get("salary_min", 0), job.get("salary_max", 0)),
            _score_badge(job.get("fit_score")),
            skills[:30],
        )
    console.print(table)


def _print_job_detail(conn, job_id: int) -> None:
    job = get_job_by_id(conn, job_id)
    if not job:
        return
    t = Table(show_header=False, box=box.SIMPLE)
    t.add_column("Field", style="bold", width=12)
    t.add_column("Value")
    t.add_row("Title", job.get("title", ""))
    t.add_row("Company", job.get("company", ""))
    t.add_row("Location", job.get("location", ""))
    t.add_row("Remote", "Yes" if job.get("remote") else "No")
    t.add_row("Skills", ", ".join(job.get("skills") or []))
    t.add_row("Exp req.", f"{job.get('experience_years', 0)} years")
    t.add_row("Salary", _fmt_salary(job.get("salary_min", 0), job.get("salary_max", 0)))
    console.print(t)


def _score_badge(score: Optional[float]) -> str:
    if score is None:
        return "[dim]—[/dim]"
    if score >= 80:
        return f"[bold green]{score}[/bold green]"
    if score >= 60:
        return f"[bold yellow]{score}[/bold yellow]"
    if score >= 40:
        return f"[yellow]{score}[/yellow]"
    return f"[red]{score}[/red]"


def _fmt_salary(lo: int, hi: int) -> str:
    if not lo and not hi:
        return "[dim]—[/dim]"
    if lo == hi or not hi:
        return f"${lo // 1000}k"
    return f"${lo // 1000}k–${hi // 1000}k"


if __name__ == "__main__":
    app()
