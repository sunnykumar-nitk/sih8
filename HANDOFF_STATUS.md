# HANDOFF STATUS -- Disaster-Resilient AI (v5)

Read this FIRST. Previous handoff kept as `HANDOFF_STATUS_v4.md` for
history; `PROJECT_REQUIREMENTS_STATUS.md` has the original v3 baseline.

This session's job: close the gaps v4 left open (frontend chat widget,
disaster_type selector) and make deployment actually reliable, without
removing any existing feature. Done in a sandbox with **no network
access**, so anything requiring `pip install` (fastapi/sqlalchemy/pytest)
or an actual `vercel deploy`/`render deploy` could not be run here --
only reasoned about via careful reading, `py_compile`, and current
Vercel documentation (fetched via web search, not local pip).

---

## 1. What changed in THIS session (v4 -> v5)

| Area | What changed | Why |
|---|---|---|
| `frontend/assistant.html` + `frontend/js/chat.js` | NEW -- full chat widget UI (mode toggle, suggestion chips, typing indicator, source/confidence display) wired to the existing `/api/chat` | v4's #1 flagged gap: backend chatbot worked, no UI existed |
| `frontend/*.html` nav | Added "AI Assistant" link to all 6 pages | so the new page is reachable |
| `frontend/assessment.html` + `js/assessment.js` | Added `disaster_type` `<select>`, wired into upload FormData, added a hint that the manual slider is overridden for named types, added display of `cascading_explanation`, `nearby_critical_facilities`, and `disaster_factor_analysis` on the result card | v4's #2 flagged gap: backend supported `disaster_type`, frontend never sent it; and computed fields existed in the API response but were never shown |
| `frontend/js/dashboard.js` | Priority-queue rows are now clickable -> jump to the Assistant page with a pre-filled question about that site | small UX improvement tying the new chat page into the existing dashboard |
| `vercel.json` | Rewritten from the legacy `builds`/`routes` format to the current (2026) documented `functions`/`rewrites` format, with explicit `includeFiles` for `frontend/**` and `backend/data/**` | de-risk deployment; see section 3 |
| `.python-version` | NEW -- pins `3.12` | avoids Vercel silently building against a newer CPython that may not yet have prebuilt wheels for opencv-python-headless/pandas, which would fail the build |
| `.env.example` | NEW -- documents every env var (`DEMO_MODE`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CHAT_MODE_DEFAULT`, `DATABASE_URL`) | there was no template before |
| `render.yaml` | NEW -- alternative deployment target with a genuinely persistent process (unlike Vercel's ephemeral `/tmp`) | requested: "some other free deployable platform" |
| `README.md` | Updated API table (added `/api/chat`, `/api/chat/status`, `disaster_type` param), updated limitations/future-improvements (several "future" items were actually already done in v4), added section 14 (deployment instructions for both platforms) | README had drifted from what v4 actually shipped |

Nothing existing was removed. All v4 backend logic is untouched except
where explicitly noted above (frontend-only changes + config files).

---

## 2. Verification actually performed this session

Same sandbox limitation as v4: no network, so no `pip install`. What I
could and did do:

- `python3 -m py_compile` on every `.py` file in `backend/` and `api/`
  -- all clean, no syntax errors introduced.
- Built a minimal local shim for the parts of `pytest` the test suite
  uses (`fixture`, `importorskip`) and a small custom runner
  (not part of the repo -- was only in my scratch environment) to
  execute the 5 test files that don't need fastapi/sqlalchemy:
  `test_scoring.py`, `test_disaster_factors.py`, `test_triage.py`,
  `test_team_sizing.py`, `test_chat_service.py`.
  **Result: all 30 tests still pass**, unchanged from v4 -- confirms
  none of this session's edits (all frontend/config, no backend logic
  touched) broke anything the backend does.
- `test_api.py` (10 tests) still could not run -- needs
  `fastapi.testclient`, unavailable without network. Still the #1 thing
  to run first after `pip install -r requirements.txt pytest httpx`.
- Manually reviewed `main.py`, `api/assessment.py`, `api/upload.py`,
  `api/teams.py`, `api/chat.py`, `services/db_service.py`,
  `config.py` line by line for correctness -- no bugs found, the DB
  wiring and API contracts all line up cleanly with what the frontend
  now expects (checked field names like `disaster_factor_analysis`,
  `matched_factors`, `cascading_explanation` against the actual
  Python return values, not just assumed).
- Checked HTML tag balance (`<div>`/`</div>` counts) on every touched
  frontend file -- all balanced.
- Verified `vercel.json` is valid JSON.

**NOT verified** (same as v4, still needs a real environment):
- `test_api.py` and the SQLAlchemy DB layer end-to-end.
- An actual `vercel deploy` or Render deployment -- I have no deploy
  access from this sandbox. Section 3 explains the reasoning behind the
  new `vercel.json`, sourced from Vercel's own docs (fetched fresh this
  session, dated as recently as July-Aug 2026), but it has not been
  deployed and watched succeed by an actual Vercel build.
- Chat online mode (Gemini) -- still needs a live key + network.

**If you can run `pip install` and `vercel deploy`/`render deploy`: do
that before trusting the deployment claims below. Trust real build/
deploy output over this document.**

---

## 3. Why `vercel.json` changed, in detail

The v4 `vercel.json` used the legacy `builds`/`routes` format:
```json
{
  "builds": [{ "src": "api/index.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "api/index.py" }]
}
```
This is a real, historically-working pattern (confirmed via several
external examples during this session's research), so it likely would
have worked. Two things pushed the change:

1. Vercel's current docs (as of this session) present `routes` as
   legacy, superseded by `rewrites`/`redirects`/`headers`, and describe
   `functions` + `includeFiles` as the current way to configure a
   specific Python function's bundle.
2. Belt-and-suspenders on the static frontend: `main.py` mounts
   `frontend/` via FastAPI's `StaticFiles` at `/`, which only works if
   those files are actually present in the deployed function's
   filesystem. Vercel's docs state Python functions include "all files
   from your project that are reachable at build time" by default, so
   this was very likely already fine even in v4 -- but the explicit
   `includeFiles: "{frontend/**,backend/data/**}"` makes it a hard
   requirement instead of an assumption.

New format:
```json
{
  "functions": { "api/index.py": { "includeFiles": "{frontend/**,backend/data/**}" } },
  "rewrites": [{ "source": "/(.*)", "destination": "/api/index" }]
}
```
`api/index.py` is unchanged -- still the same thin entrypoint that
imports `app` from `backend/main.py`. If this new config ever causes a
build issue that the old one didn't, reverting to the v4 `builds`/
`routes` block is a safe fallback (it's saved in `HANDOFF_STATUS_v4.md`'s
description / the v4 zip).

**Considered but deliberately NOT done:** restructuring the whole repo
to move `frontend/` contents into a root `public/` directory, which is
Vercel's other documented static-serving method, fully decoupled from
the Python function. Doing that would mean serving the frontend two
different ways on two different platforms (`public/` on Vercel,
`StaticFiles` mount on Render/local), doubling the maintenance surface
for a benefit (marginally faster static asset serving) that doesn't
matter for a hackathon demo. If static-file bundling ever turns out to
be a real problem on Vercel despite `includeFiles`, that's the next
thing to try -- not before.

---

## 4. Everything still true from v4 (not re-verified, no reason to think it changed)

- No trained YOLO model -- `HeuristicDamageDetector` (OpenCV heuristics)
  is still the only detector.
- No real road-network routing -- haversine straight-line distance only.
- Population estimate is still a modeled approximation (REFERENCE DATA
  for 3 named regions, DEMO DATA elsewhere).
- Cascading impact is proximity-based, not a true dependency graph.
- DB layer (SQLAlchemy) unverified end-to-end -- see section 2.
- `test_api.py` (10 tests) unverified -- see section 2.
- Chat online mode (Gemini) unverified -- see section 2.

## 5. Suggested next steps, in order

1. `pip install -r requirements.txt pytest httpx && cd backend && pytest -v`
   -- confirm all 40 tests pass (30 already confirmed in this sandbox,
   10 in `test_api.py` still need this).
2. `uvicorn main:app --reload --port 8000` locally, open
   `http://localhost:8000/dashboard.html`, run through: upload an
   assessment (try a named `disaster_type`, confirm the new fields show
   on the result card) -> check the dashboard -> click a priority row
   (confirm it jumps to the Assistant page and gets an answer) -> ask
   the Assistant a few questions directly -> register a team and run
   allocation -> generate a PDF report.
3. Restart the server, `GET /api/sites` again -- confirm sites survived
   (DB persistence check the v4 doc asked for and this session couldn't
   run).
4. Push to GitHub, deploy to Vercel per README section 14. Watch the
   build log for any Python wheel-build failures (the reason for
   `.python-version` pinning 3.12) or missing-file errors on the
   frontend routes (the reason for `includeFiles`).
5. Optionally also deploy the `render.yaml` target and compare -- keep
   whichever one actually holds data reliably across your demo session.
6. Set `GEMINI_API_KEY` on whichever platform you keep, to light up
   online chat mode.

---

## 6. v5 -> v6: Vercel deployment was actually broken -- root cause + fix

The user reported `{"detail":"Not Found"}` on the live Vercel deployment.
That JSON shape is FastAPI's own default 404 -- meaning the function WAS
running, it just couldn't find the frontend files to serve.

**Root cause:** Vercel changed how it supports FastAPI recently (per their
current docs, fetched 2026-08-29). There's now a "zero-config" mode that
auto-detects a FastAPI `app` instance at a supported entrypoint
(`app.py`/`index.py`/`server.py`/`main.py`/`wsgi.py`/`asgi.py` at the
project root or under `src/`/`app/`) and, critically, **auto-promotes
`app.mount(..., StaticFiles(...))` calls to Vercel's CDN at build time**.

This project's `backend/main.py` isn't at any of those auto-detected
paths, so earlier sessions worked around it with a hand-rolled
`api/index.py` that imported and re-exported the app (the OLD, pre-
zero-config convention: any `.py` file under `/api/` becomes its own
isolated file-based function), plus a `vercel.json` rewrite sending every
request through it. That still runs the FastAPI app correctly (hence API
routes like `/api/health` would have worked), but it predates -- and does
not get -- the automatic StaticFiles-to-CDN promotion, so the
`app.mount("/", StaticFiles(directory=_FRONTEND_DIR))` call in
`backend/main.py` never actually got the frontend files served correctly
in that environment, causing every non-API path (including `/`) to 404.

**Fix applied this session:**
1. Added `pyproject.toml` at the project root:
   ```toml
   [tool.vercel]
   entrypoint = "backend.main:app"
   ```
   This is Vercel's documented way to point zero-config detection at a
   FastAPI app in a custom module location, and is what unlocks the
   automatic static-file promotion.
2. Added `backend/__init__.py` (empty) so `backend` is an importable
   package, required for the dotted `backend.main:app` entrypoint syntax.
3. **Deleted the `api/` directory entirely** (`api/index.py` removed).
   Leaving it in place risks Vercel treating it as an ADDITIONAL legacy
   file-based function alongside the new zero-config detection, which is
   likely to cause routing conflicts, not just redundancy.
4. Simplified `vercel.json` to just a `functions` block keyed by the
   resolved entrypoint path (`backend/main.py`) for `maxDuration` --
   removed the old `rewrites` block and the `includeFiles` config, both
   unnecessary now (Vercel's Python builder already bundles the whole
   project by default, and CDN promotion handles the frontend).
5. Updated `README.md`'s deployment section to match.

**NOT verified end-to-end** -- this sandbox has no network access, so the
actual Vercel build/deploy couldn't be re-run here. The fix is based on
Vercel's current official documentation (fetched live in this session:
`vercel.com/docs/frameworks/backend/fastapi`), which explicitly describes
this exact mount pattern (`app.mount("/", StaticFiles(...))`, mount
declared after the API routers) as supported and auto-promoted. All
Python files still `py_compile` clean after the change.

**What whoever deploys this next needs to do:**
1. Push this to GitHub (replacing the old `api/index.py`-based version --
   git will show `api/index.py` deleted, `pyproject.toml` and
   `backend/__init__.py` added, `vercel.json` changed).
2. Redeploy on Vercel (should trigger automatically on push to `main`, per
   the "Production Checklist" in the dashboard the user showed).
3. Check `/api/health` first (should return `{"status":"healthy"}` --
   confirms the function itself is running).
4. Then check `/` (should now serve `frontend/index.html`, not 404).
5. If `/` still 404s after this, the next thing to check is whether
   `frontend/` and `backend/data/` actually made it into the Git repo (a
   stray `.gitignore` entry would silently exclude them from the deploy
   even though they're present locally) -- there was no `.gitignore` in
   the zip provided to this session, so this couldn't be checked here.

---

## 7. v6 -> v7: the v6 fix above ALSO failed -- `pyproject.toml` broke the build entirely

The v6 fix (section 6) was based on correctly-read current Vercel docs,
but had one untested consequence: **the mere presence of a
`pyproject.toml` file switches Vercel's Python builder to `uv` for
dependency installation**, regardless of what's actually inside that
file. The build log the user provided showed:

```
Installing required dependencies from pyproject.toml...
Error: Failed to run "uv lock --python ...": ...
error: No `project` table found in: /vercel/path0/pyproject.toml
```

Our v6 `pyproject.toml` only had a `[tool.vercel]` section (for the
`entrypoint` override) -- no PEP 621 `[project]` table with
name/version/dependencies, which `uv lock` requires unconditionally once
it sees the file at all. Requirements.txt was apparently ignored entirely
once pyproject.toml existed. **This means the v6 zip's deployment
instructions never actually worked -- the build failed before the app
code ever ran.** Confirmed via a live build log the user pasted from
their actual Vercel deployment attempt, not something guessed at.

**v7 fix:** abandon the `pyproject.toml` / `[tool.vercel] entrypoint`
approach entirely. Instead:
1. Deleted `pyproject.toml` and `backend/__init__.py` (no longer needed).
2. Added a root-level `index.py` -- one of Vercel's directly auto-detected
   zero-config entrypoint filenames (`app.py`/`index.py`/`server.py`/
   `main.py`/`wsgi.py`/`asgi.py`), so NO pyproject.toml override is
   needed at all. It's a 15-line shim: adds `backend/` to `sys.path`,
   then `from main import app`.
   - Named `index.py`, deliberately NOT `main.py` -- if the root shim
     were also called `main.py`, `from main import app` would try to
     re-import itself once `backend/` is on `sys.path`, instead of
     reaching `backend/main.py`. Verified this actually resolves to
     `backend/main.py` (not the shim itself) via `importlib.util.find_spec`
     in this session -- see the file's own docstring for the full
     reasoning.
   - Kept at the project ROOT, not under `api/` -- putting it under
     `api/` would activate the OLD "file-based Python functions in
     `/api`" convention (what v5 used, and what v6 was trying to move
     away from), not the zero-config detection this fix depends on.
3. Updated `vercel.json`'s `functions` key from `"backend/main.py"` to
   `"index.py"` (the key must match the actual resolved entrypoint file).
4. Updated `README.md`'s deployment section again to match, and to
   explicitly warn against re-adding a `pyproject.toml` for this purpose.

**Still NOT verified end-to-end** -- same sandbox limitation as before
(no network access to actually run `vercel build`). What WAS verified
directly in this session: the shim's import resolves to the real
`backend/main.py` and not itself (ran it with `importlib.util.find_spec`),
and every `.py` file in the project still `py_compile`s cleanly. The
`uv`/`pyproject.toml` failure mode itself is corroborated by the actual
build log the user pasted, not a guess -- but the FIX for it (root-level
`index.py` shim) has not been confirmed against a real Vercel build.
**Whoever deploys this next should treat this as the most important thing
to verify first**, before trusting anything else in this document.


---

## 8. File map (cumulative: v4 -> v5 -> v6 -> v7 changes)

```
frontend/assistant.html                     (NEW -- chat UI)
frontend/js/chat.js                         (NEW -- chat UI logic)
frontend/dashboard.html                     (edited -- nav link, clickable rows)
frontend/assessment.html                    (edited -- nav link, disaster_type select)
frontend/map.html                           (edited -- nav link)
frontend/teams.html                         (edited -- nav link)
frontend/reports.html                       (edited -- nav link)
frontend/js/assessment.js                   (edited -- disaster_type wiring, result card additions)
frontend/js/dashboard.js                    (edited -- clickable priority rows)
vercel.json                                 (rewritten -- modern functions/rewrites format)
.python-version                             (NEW -- pins 3.12)
.env.example                                (NEW)
render.yaml                                 (NEW -- alternative deploy target)
README.md                                   (edited -- API table, limitations, deployment section)
HANDOFF_STATUS.md                           (this file)
HANDOFF_STATUS_v4.md                        (NEW -- previous handoff, kept for history)
pyproject.toml                              (NEW in v6, DELETED again in v7 -- see sections 6/7)
backend/__init__.py                         (NEW in v6, DELETED again in v7 -- no longer needed)
api/index.py                                (DELETED, v6 -- legacy entrypoint, see section 6)
index.py                                    (NEW, v7 -- root-level entrypoint shim, see section 7)
vercel.json                                 (rewritten again, v6; functions key updated again, v7)
README.md                                   (edited again, v6 and v7 -- deployment section)
```

No backend application LOGIC was changed this session -- every `.py`
file's runtime behavior is identical to v4. The only Python changes were
structural/deployment-related: `backend/__init__.py` added (empty marker
file) and `api/index.py` deleted (see section 6). Nothing in
`notebooks/`, `backend/main.py`, or any `backend/api|services|
recommendation|models` file's actual code was touched.
