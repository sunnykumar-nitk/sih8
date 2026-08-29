# Daring Dicey -- Disaster-Resilient Infrastructure Assessment

Smart India Hackathon 2026 -- NITK Surathkal

AI-assisted post-disaster assessment and emergency inspection
prioritization. **The AI never certifies repairs -- qualified personnel
make the final call.** This is a decision-support prototype, not a
structural safety certifier.

## 1. Project idea

Transforms raw disaster imagery into a prioritized, ready-to-execute
field inspection plan:

```
Collect Data -> Detect Damage -> Assess Risk & Impact -> Priority List
-> Inspection Plan -> Guide the Team -> Findings & Report
```

Every flagged site gets a transparent 0-100 priority score built from
damage severity, population impact, infrastructure importance,
accessibility, disaster conditions, cascading dependency risk, and more
-- plus concrete recommendations (immediate safety action, temporary
mitigation, quick-fix vs. reroute comparison, required team/equipment,
and a final PDF report).

## 2. Architecture

```
backend/
  main.py            FastAPI app entrypoint
  config.py           All weights/thresholds/importance values (tunable)
  api/                 HTTP routes (upload, assess, recommendations, teams, reports)
  models/               AI-facing layer: damage_detector, severity_model, risk_model
  services/              Data providers: image, gis, population, routing, disaster, report
  recommendation/         Decision layer: scoring, triage, mitigation, team_allocation, route_planner
  data/                    infrastructure.csv, teams.csv, demo_cases/*.json
frontend/
  *.html + css/js       Plain HTML/CSS/JS dashboard (no build step needed)
                          -- includes assistant.html, the AI Q&A chat UI
notebooks/
  01-06                Block-by-block Jupyter notebooks mirroring the backend logic
generated_reports/     PDF output lands here
```

**Design principle:** AI detects evidence -> a deterministic scoring
engine calculates priority -> recommendations are generated from rules,
not invented by an LLM. This keeps the system explainable and easy to
defend to judges.

## 3. Installation

```bash
cd disaster_resilient_ai
pip install -r requirements.txt
```

## 4. Running the backend locally

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs for interactive API docs (Swagger UI) --
you can test every endpoint directly from the browser.

## 5. Running the frontend

The frontend is plain HTML/CSS/JS -- no build step. Just open
`frontend/dashboard.html` directly in a browser **while the backend is
running** (it calls `http://localhost:8000/api`). If your browser blocks
local file requests, serve it with:

```bash
cd frontend
python3 -m http.server 5500
# then visit http://localhost:5500/dashboard.html
```

## 6. Using the notebooks (Google Colab or local Jupyter)

Each notebook in `notebooks/` is self-contained and block-wise (one
concept per cell, comments explaining each step):

| Notebook | Covers |
|---|---|
| 01_data_preparation | Loading/validating infrastructure.csv + teams.csv |
| 02_damage_detection | Mock vs. real (YOLO) detector adapter |
| 03_severity_model | Detections -> 0-10 severity score |
| 04_priority_model | Severity + context -> 0-100 priority score |
| 05_team_allocation | Matching limited teams to prioritized sites |
| 06_demo_cases | Full pipeline on Nepal flood / Assam flood / Ahmedabad crash |

**Google Colab:** File -> Upload notebook, upload the `.ipynb`, then also
upload the `backend/` folder (or mount Drive) so the `sys.path.append`
imports resolve -- easiest is to upload the whole `disaster_resilient_ai`
folder to Drive and open notebooks from there.

## 7. Demo cases

Three required scenarios are pre-loaded as JSON in
`backend/data/demo_cases/`: `nepal_flood.json`, `assam_flood.json`,
`ahmedabad_crash.json`. These currently use labeled DEMO DATA (not real
detections) -- **upload real images for these events via `/api/upload`
or the Assessments page to replace mock data with live analysis.**

## 8. Model training (not included -- your team's YOLO model)

This project ships with `HeuristicDamageDetector`, which lets the entire
pipeline run today without a trained model. **It is not a placeholder
that fakes results from filenames** -- it actually analyzes each image's
pixels with OpenCV (water-color coverage -> flooding, fire-color coverage
-> fire, edge/crack density via Canny -> structural damage/cracks) so a
real photo of a flooded road will genuinely score differently from a
real photo of a fire. It is a legitimate, defensible stand-in for a
trained model -- just not deep-learning-based yet. Once your team trains
a YOLO model in Colab:

1. Export weights to `backend/models/weights/best.pt`
2. Set `DEMO_MODE=false` (environment variable)
3. `get_detector()` in `damage_detector.py` automatically switches to
   `YOLODamageDetector` -- no other code changes required.

## 9. API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | /api/upload-batch | **Main demo flow.** Upload 1-15 photos and/or videos for one case (e.g. "Nepal Flood") -- videos are auto-split into up to 5 frames each, everything is pooled into one aggregated site assessment |
| POST | /api/upload | Upload a single image, quick detection preview only |
| GET | /api/preview-image?path=... | Serves an uploaded/extracted frame back to the frontend for display |
| POST | /api/assess | Score a site's full priority (0-100) from manually-entered factors (no image) |
| GET | /api/sites | List all assessed sites this session |
| GET | /api/sites/{id} | Get one site |
| GET | /api/priority | Sites sorted by priority, highest first |
| GET | /api/recommendations/{id} | Immediate safety / mitigation / inspection need |
| POST | /api/recommendations/fix-vs-reroute | Compare quick-fix vs. detour time |
| POST | /api/teams | Register a response team |
| GET | /api/teams | List teams |
| POST | /api/allocate | Auto-assign teams to prioritized sites |
| POST | /api/report | Generate PDF report |
| GET | /api/report/{filename} | Download a generated PDF |
| POST | /api/chat | AI Q&A -- ask about any assessed site; answers are always grounded in real data, never invented. `mode`: "offline" (free rule-based), "online" (Gemini, needs `GEMINI_API_KEY`), or "auto" (default) |
| GET | /api/chat/status | Whether online chat mode is configured, and how many sites exist to ask about |

`POST /api/upload-batch` also accepts a `disaster_type` form field
(`"flood"` \| `"earthquake"` \| `"aircraft_crash"` \| `"generic"`, default
`"generic"`) -- for a named type, `disaster_conditions` is computed from
which disaster-specific evidence (flood depth, structural tilt, fire,
etc. -- see `config.DISASTER_FACTORS`) actually shows up in the uploaded
imagery, instead of using the manual slider value.

## 10. Configuration

All weights, thresholds, and infrastructure-importance defaults live in
`backend/config.py`. **These are configurable starting points for a
hackathon prototype, not official engineering standards** -- tune them
with your team.

## 11. Scoring formula (summary)

```
priority_score (0-100) = weighted sum of:
  damage_severity, population_impact, infrastructure_importance,
  accessibility, disaster_conditions, critical_facility_impact,
  cascading_impact, human_impact, time_sensitivity,
  alternative_route_risk, data_confidence
```

Classified into CRITICAL / HIGH / MEDIUM / LOW using configurable
thresholds in `config.py`.

## 12. Limitations (be upfront with judges about these)

- All GIS/population/routing data is **DEMO DATA** by default -- clearly
  labeled, not real census/routing data, until real providers are wired in.
- `HeuristicDamageDetector` uses real pixel-color/edge analysis (OpenCV),
  not a trained neural network -- it will misjudge damage types that
  don't have a strong color/texture signature (e.g. subtle hairline
  cracks, damage that doesn't involve water/fire/heavy edges). Swap for
  a trained YOLO model for production-grade accuracy.
- The site/team store is in-memory, mirrored to a SQLite database on
  every write (`backend/services/db_service.py`) so it survives an
  ordinary process restart. On serverless platforms (Vercel), the
  writable directory (`/tmp`) is wiped on cold starts, so persistence
  there only lasts while a function instance stays warm -- see section
  14 for a genuinely-persistent alternative.
- Team allocation uses a simple greedy matching algorithm, not a formal
  optimizer -- upgradeable to the Hungarian algorithm if needed.
- Cascading-impact language is proximity-based (is a facility within
  `radius_km`?), not a true road-network dependency graph (e.g. "Bridge A
  is the ONLY route to Hospital B"). See
  `recommendation/triage.py::build_cascading_explanation` docstring.
- The chatbot's online mode (Gemini) is optional and untested against a
  live key in an offline sandbox -- the offline rule-based mode is always
  available and needs no key.

## 13. Future improvements

- Real YOLO-trained damage detection model
- Real open-data GIS/population/routing providers (OpenStreetMap/Overpass, etc.)
- A true road/bridge -> facility dependency graph for cascading impact
  (not just proximity)
- Hosted Postgres for real persistence on serverless deployments
- Authentication for the dashboard

## 14. Deployment

Two supported targets -- pick based on whether you need real persistence:

### Vercel (serverless, easiest, free)

1. Push this repo to GitHub.
2. On [vercel.com](https://vercel.com): New Project -> import the repo.
   `vercel.json`, root `index.py`, and `.python-version` are already set
   up -- no manual configuration needed. Vercel's zero-config FastAPI
   detection finds the `app` instance via the root-level `index.py` shim
   (one of Vercel's auto-detected entrypoint filenames), which points at
   the real app in `backend/main.py`. This also gets the
   `app.mount("/", StaticFiles(...))` call in `backend/main.py`
   auto-promoted to Vercel's CDN, which is what actually serves the
   frontend.
   **Do NOT add a `pyproject.toml`** to try to customize the entrypoint
   location instead -- its mere presence switches Vercel's Python builder
   to `uv`, which requires a full `[project]` table (name/version/
   dependencies) or the build fails outright with `No \`project\` table
   found`. This project intentionally uses the plain `requirements.txt` +
   root-level shim approach instead; see `HANDOFF_STATUS.md` section 6/7
   for the two dead ends already tried here.
3. In Project Settings -> Environment Variables, optionally set
   `GEMINI_API_KEY` (enables online chat mode) and `DATABASE_URL` (point
   at a hosted Postgres for real persistence -- see below).
4. Deploy. Visit the assigned `*.vercel.app` URL.

**Persistence caveat:** Vercel Functions are serverless -- only `/tmp` is
writable, and it's wiped on every cold start. The SQLite database
(`db_service.py`) will work, but "persists" only while a function
instance stays warm, not across cold starts. For real persistence on
Vercel, set `DATABASE_URL` to a free hosted Postgres (e.g.
[Neon](https://neon.tech) or [Supabase](https://supabase.com)) -- the
SQLAlchemy layer doesn't care which database it's pointed at, only the
URL changes.

### Render (persistent process, free tier)

`render.yaml` is included at the repo root. On
[render.com](https://render.com): New -> Blueprint -> connect the repo --
Render reads `render.yaml` automatically and runs
`uvicorn main:app` as a normal long-running process, so the SQLite file
genuinely persists across ordinary requests and idling (not across a
redeploy, unless you attach a paid persistent disk). This is the more
reliable option if you want the database to actually hold data between
demo sessions without paying for hosted Postgres.

### Either platform

Set `GEMINI_API_KEY` in the platform's environment variable settings to
enable online chat mode; leave it unset and the app runs fully offline
at $0 cost, same as local dev. See `.env.example` for every variable.
