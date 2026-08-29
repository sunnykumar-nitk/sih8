"""
Vercel zero-config entrypoint.

Vercel's Python/FastAPI zero-config detection looks for a FastAPI `app`
instance at one of a few default TOP-LEVEL filenames: app.py, index.py,
server.py, main.py, wsgi.py, or asgi.py. Our real app lives at
backend/main.py, so this file is a thin shim: it puts backend/ on
sys.path and re-exports the app from there.

Deliberately named `index.py`, NOT `main.py` -- if this file were also
called main.py, "from main import app" below would try to re-import
itself instead of backend/main.py once backend/ is added to sys.path,
since Python would find THIS file first under that name.

Note: this file must stay at the PROJECT ROOT, not under api/. Putting
it under api/ activates Vercel's older "file-based Python functions in
the /api directory" convention (each .py file becomes its own isolated
function, no static-asset auto-promotion) instead of the newer
zero-config FastAPI detection that this project relies on to serve
frontend/ automatically -- see HANDOFF_STATUS.md section 6 for the full
story of why that distinction matters here.

Deliberately NOT using a pyproject.toml `[tool.vercel] entrypoint`
override for this instead: as soon as a pyproject.toml exists, Vercel's
builder switches to `uv` for dependency installation, which requires a
full PEP 621 `[project]` table (name/version/dependencies) or the build
fails with "No `project` table found". This project's dependencies are
declared in the plain requirements.txt at the root instead, and this
root-level shim avoids needing pyproject.toml at all.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from main import app  # noqa: E402
