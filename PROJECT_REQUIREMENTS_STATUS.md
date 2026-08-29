# Daring Dicey -- Requirements & Completion Status

Legend: ✅ Done & tested this session · 🟡 Partially done / simplified · ❌ Not built yet

---

## What changed in this session (all tested, not just written)

| Change | Status | Proof |
|---|---|---|
| Upload limit: separate 10 photos + 10 videos (was a combined 15) | ✅ | tested: 11 photos → HTTP 400 "Max 10 photos per batch"; 10 photos → 200 OK |
| Population estimate driven by what's VISIBLE in the imagery, not just the pin | ✅ | tested: same location, 90%-flooded photo → 3,186 people; 20%-flooded photo → 717 people. Real signal, not a fixed radius. |
| `image_coverage` transparency block in the API response + result card | ✅ | shows `avg_affected_fraction`, `area_per_file_km2` (default 0.8, overridable), `surveyed_area_km2`, `estimated_affected_area_km2` |
| Dashboard: "People Potentially Affected" + "Personnel Needed" summary cards | ✅ | confirmed both fields (`population_data`, `team_size`) exist on every site record and the cards sum them correctly |

## Full verification of the pre-existing v2 build (before I touched anything)

I did not take the previous status doc's word for it -- I unzipped your file, read the actual source, installed the real dependencies, and ran it:

| Claim | Verified? |
|---|---|
| `team_sizing.py` exists and produces role-by-role headcounts | ✅ real file, read in full |
| `population_service.py` has REFERENCE DATA for Nepal/Assam/Ahmedabad + DEMO DATA fallback elsewhere | ✅ real file, read in full |
| Vercel deployment config (`api/index.py`, `vercel.json`) | ✅ present |
| App imports and runs without errors | ✅ ran `TestClient` against the live app |

---

## Known gaps (unchanged from before, still accurate)

| Requirement | Status | Notes |
|---|---|---|
| Disaster-specific factor sets wired into scoring (flood ≠ earthquake ≠ crash) | 🟡 | `config.DISASTER_FACTORS` lists the right factors per type but the scoring formula doesn't branch on disaster type yet |
| Real road-network routing (actual streets) | 🟡 | still haversine straight-line distance, not OSRM/Google Directions |
| Cascading dependency graph + explanation sentences ("Bridge A → Hospital B") | 🟡 | a `cascading_impact` number exists; the actual dependency chain/sentence generator doesn't |
| AI Q&A chatbot ("Why is Bridge A critical?") | ❌ | no `/api/chat` endpoint exists |
| Persistent storage (SQLAlchemy/SQLite instead of in-memory dict) | ❌ | site/team data resets on server restart |
| Automated test suite (15+ tests) | ❌ | verification so far is manual `TestClient` calls in-session, not a committed pytest suite |
| YOLO-trained detection model | ❌ | `HeuristicDamageDetector` (real pixel analysis, not filenames) is the only detector running -- architecture is ready for a trained model, none exists yet |

## Honest limitation on the new image-driven population feature

`area_per_file_km2` (default 0.8 km² per photo) is an assumption, not measured from real drone telemetry (altitude, sensor size, GSD) -- if you know your actual drone's ground coverage per shot, override it via the `area_per_file_km2` form field for a much more accurate number. Right now it's a reasonable placeholder, documented as such in the code.

---

Tell me which gap to close next and I'll build it the same way: implement it, then actually run it and show you real numbers before handing it back.
