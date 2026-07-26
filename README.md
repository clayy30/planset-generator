# Planset Generator

**Doctor Planset** — a UI + API that builds permit-grade PV / hybrid ESS plansets **better than typical Solar Permit Solutions–style CAD exports**.

## Quality commitment

Compared to common 11×17 permit packages (e.g. boilerplate PV-0…PV-6 with weak calcs):

| Area | Permit-mill norm | This generator |
|------|------------------|----------------|
| Cover kWAC | Often marketing / nameplate confusion | **Continuous inverter output only** |
| String design | Numbers without work | **Voc_cold formula + PASS/FAIL** |
| 705 busbar | Sometimes missing | **120% rule with formula** when backfeed |
| Hybrid / dual 200A | Rarely correct | **Half-home & full dual-disco SLD** |
| QA | Absent | **PV-7 checklist sheet** |
| Typos / code cites | “NCE”, recycled notes | Clean NEC framing + topology notes |

Still **not a PE stamp** — EC/PE/AHJ remain authority. It is a serious design package, not a flyer.

## Sheets

- **PV-0** Cover / system summary  
- **PV-1** Site & project data  
- **PV-2** Array & attachment basis  
- **PV-3** Single-line diagram  
- **PV-4** Electrical calculations (work shown)  
- **PV-5** Wire schedule & BOM  
- **PV-6** Labels & placards  
- **PV-7** QA / AHJ checklist  

## Run

```bash
cd /Users/cc/planset-generator
./run.sh
# uses python3.13 when available (3.14 may lack pydantic wheels)
```

Or manually:

```bash
cd /Users/cc/planset-generator
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8787
```

Open **http://127.0.0.1:8787/**

1. Load **Duracell 400A preset** or fill the wizard  
2. Preview calculations  
3. **Generate planset** → open HTML → Print → PDF (11×17 / ANSI B landscape)

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health + quality commitment |
| GET/POST | `/api/projects` | List / create |
| GET/PUT/DELETE | `/api/projects/{id}` | CRUD |
| POST | `/api/preview-calcs` | Dry-run electrical math |
| POST | `/api/generate` | Save + render planset |
| GET | `/api/projects/{id}/planset` | HTML planset |
| GET | `/api/presets/duracell-400a` | 400A dual-disco hybrid preset |
| GET | `/api/presets/eg4-gridboss` | EG4-style sample |

## Layout

```
planset-generator/
  backend/app/     FastAPI, models, calcs, Jinja templates
  frontend/        Wizard UI
  data/projects/   Saved JSON
  output/          Generated HTML
```
