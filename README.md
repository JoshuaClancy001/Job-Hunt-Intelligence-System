# Job Hunt Intelligence System

Local-first job tracking with AI-powered fit scoring, cover letter generation, and application analytics. No cloud, no Docker, no paid APIs required.

## Quick Start

```bash
# 1. Create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies and seed demo data
pip install -r requirements.txt && python cli.py demo
```

That's it. The demo loads 5 sample jobs, scores them against the built-in profile, and displays a rich table with fit scores.

## Setup Your Profile

Edit `profile.json` with your real skills, experience, and preferences:

```bash
# After editing profile.json:
python cli.py profile --load
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python cli.py demo` | Load sample data and run the full pipeline |
| `python cli.py scrape --url URL` | Scrape a job posting URL |
| `python cli.py analyze` | Parse and score all jobs against your profile |
| `python cli.py apply --job-id ID --status applied` | Track an application status |
| `python cli.py insights` | Show application funnel and key metrics |
| `python cli.py generate --job-id ID --type cover-letter` | Generate a cover letter |
| `python cli.py generate --job-id ID --type both` | Cover letter + resume bullets |
| `python cli.py profile` | Show your candidate profile |
| `python cli.py profile --load` | Reload profile from profile.json |

Application statuses: `saved` → `applied` → `phone` → `onsite` → `offer` / `rejected`

## Web UI (Optional)

A React frontend is included for a visual interface:

```bash
# Terminal 1 — start the API backend (activate venv first)
source .venv/bin/activate && python main.py
# → http://localhost:8080/docs

# Terminal 2 — start the frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

## LLM Enhancement via Ollama (Optional)

If [Ollama](https://ollama.ai) is installed and running, the parser and writer agents use it automatically for richer extraction and more personalized cover letters:

```bash
ollama pull llama3
# Ollama runs at localhost:11434 — no config needed
python cli.py generate --job-id 1 --type cover-letter
```

Everything gracefully falls back to regex parsing and template generation if Ollama isn't running.

## Architecture

```
cli.py               ← primary interface (Typer + Rich terminal UI)
main.py              ← optional FastAPI server for the web UI
├── app/db/          ← SQLite auto-create, CRUD helpers (database.py)
├── app/models/      ← Pydantic v2 schemas (models.py)
├── app/agents/
│   ├── fit_scorer.py   100-pt scoring against your profile
│   ├── parser.py       regex + optional Ollama field extraction
│   ├── writer.py       cover letter + bullets (Ollama or template)
│   └── insights.py     application funnel metrics
├── app/scraper/     ← BeautifulSoup scraper (+ optional Playwright)
└── app/services/    ← demo data loader
frontend/            ← React + Vite + Tailwind web UI
```

### Scoring breakdown

| Component | Points | Logic |
|-----------|--------|-------|
| Skill match | 40 | Fraction of required skills you have |
| Experience match | 30 | Linear scale vs. required years |
| Role match | 20 | Job title contains a preferred role |
| Salary match | 10 | Job salary >= your minimum |

Missing data is never penalised — absent info earns neutral half-points.

## Data

All data is stored in `jobs.db` (SQLite) in the project root. To reset:

```bash
rm jobs.db && python cli.py demo
```
