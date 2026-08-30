"""
POST /api/upload       -- single image, quick detection preview (used by
                           the old single-file flow / notebooks).
POST /api/upload-batch  -- the real demo flow: multiple photos AND/OR
                           videos in one request, aggregated into ONE
                           case assessment (e.g. "Nepal Flood"). Works
                           with anywhere from 1 to MAX_FILES_PER_BATCH
                           files. Videos are broken into sampled frames
                           and analyzed the same way as photos.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
import io
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.image_service import (
    validate_file, save_upload, is_video, extract_frames, cleanup_frames,
    MAX_IMAGES_PER_BATCH, MAX_VIDEOS_PER_BATCH,
)
from services.population_service import get_population_impact
from services.gis_service import get_importance_score, find_nearby_critical_facilities
from models.damage_detector import get_detector
from models.severity_model import calculate_severity
from recommendation.scoring import calculate_priority
from recommendation.mitigation import (
    get_immediate_safety, get_temporary_mitigation, get_inspection_recommendation,
    get_team_and_equipment, build_reason,
)
from recommendation.triage import build_cascading_explanation
from recommendation.team_sizing import estimate_team_size
from recommendation.disaster_factors import compute_disaster_conditions
from api.assessment import SITE_STORE
from services import db_service

router = APIRouter()
detector = get_detector()


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        validate_file(file.filename, len(contents))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    saved_path = save_upload(io.BytesIO(contents), file.filename)
    detections = detector.detect(saved_path)
    severity = calculate_severity(detections)

    return {
        "file_path": saved_path,
        "detections": detections,
        "severity": severity,
        "detector_used": detections[0]["source"] if detections else "NONE",
    }


def _most_common(values: List[str]) -> Optional[str]:
    if not values:
        return None
    return max(set(values), key=values.count)


@router.post("/upload-batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    case_name: str = Form(...),
    asset_type: str = Form("infrastructure"),
    disaster_type: str = Form("generic"),  # "flood" | "earthquake" | "aircraft_crash" | "generic"
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    accessibility: float = Form(5),
    disaster_conditions: float = Form(5),
    area_per_file_km2: float = Form(0.8),
):
    """
    Accepts up to 10 images AND up to 10 videos (20 files max) in one
    request, any mix. Every image is analyzed directly; every video has
    up to 5 frames sampled and each frame analyzed the same way. All
    detections across the whole batch are pooled into ONE aggregated
    site assessment for `case_name`.

    Population-affected is estimated from what's actually visible in the
    uploaded imagery (fraction of each frame showing flood/fire/debris)
    multiplied by an assumed ground-area-per-photo, then multiplied by
    the population density for the selected location -- not just a fixed
    search radius around the pin. See services/population_service.py for
    the REFERENCE DATA vs DEMO DATA distinction on density itself.

    area_per_file_km2: how much ground area one photo/video is assumed to
    cover (default 0.8 km^2, a reasonable rough estimate for a drone/aerial
    shot). Override this if you know your actual drone altitude/GSD --
    it directly scales the population estimate.
    """
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="Upload at least 1 file.")

    n_images = sum(1 for f in files if not is_video(f.filename))
    n_videos = sum(1 for f in files if is_video(f.filename))
    if n_images > MAX_IMAGES_PER_BATCH:
        raise HTTPException(status_code=400, detail=f"Max {MAX_IMAGES_PER_BATCH} photos per batch (got {n_images}).")
    if n_videos > MAX_VIDEOS_PER_BATCH:
        raise HTTPException(status_code=400, detail=f"Max {MAX_VIDEOS_PER_BATCH} videos per batch (got {n_videos}).")

    all_detections = []
    processed_files = []
    preview_image_path = None
    frame_dirs_to_clean = []
    per_file_affected_fractions = []

    for f in files:
        contents = await f.read()
        try:
            validate_file(f.filename, len(contents))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"{f.filename}: {e}")

        saved_path = save_upload(io.BytesIO(contents), f.filename)

        if is_video(f.filename):
            frame_paths = extract_frames(saved_path)
            if frame_paths:
                frame_dirs_to_clean.append(frame_paths)
                if preview_image_path is None:
                    import shutil as _shutil
                    permanent_preview = os.path.join(os.path.dirname(saved_path), f"preview_{os.path.basename(frame_paths[0])}")
                    _shutil.copy(frame_paths[0], permanent_preview)
                    preview_image_path = permanent_preview
                frame_fractions = []
                for fp in frame_paths:
                    dets = detector.detect(fp, asset_type_hint=asset_type if asset_type != "infrastructure" else None)
                    all_detections.extend(dets)
                    if hasattr(detector, "estimate_affected_fraction"):
                        frame_fractions.append(detector.estimate_affected_fraction(fp))
                if frame_fractions:
                    per_file_affected_fractions.append(sum(frame_fractions) / len(frame_fractions))
            processed_files.append({"filename": f.filename, "type": "video", "frames_analyzed": len(frame_paths)})
        else:
            if preview_image_path is None:
                preview_image_path = saved_path
            dets = detector.detect(saved_path, asset_type_hint=asset_type if asset_type != "infrastructure" else None)
            all_detections.extend(dets)
            if hasattr(detector, "estimate_affected_fraction"):
                per_file_affected_fractions.append(detector.estimate_affected_fraction(saved_path))
            processed_files.append({"filename": f.filename, "type": "image", "frames_analyzed": 1})

    for frame_paths in frame_dirs_to_clean:
        cleanup_frames(frame_paths)

    if not all_detections:
        raise HTTPException(status_code=422, detail="Could not analyze any of the uploaded files (unreadable image/video data).")

    # --- Aggregate detections across the whole batch into one severity read ---
    severity = calculate_severity(all_detections)
    detected_object_types = [d["object_type"] for d in all_detections if d.get("object_type")]
    inferred_asset_type = asset_type if asset_type != "infrastructure" else (_most_common(detected_object_types) or "infrastructure")

    # --- Affected-area estimate, derived from what the images actually show ---
    avg_affected_fraction = round(sum(per_file_affected_fractions) / len(per_file_affected_fractions), 3) if per_file_affected_fractions else 0.0
    n_files = len(processed_files)
    surveyed_area_km2 = round(area_per_file_km2 * n_files, 3)
    affected_area_km2 = round(surveyed_area_km2 * avg_affected_fraction, 3)

    # --- Contextual enrichment (GIS/population) ---
    location = {"lat": lat, "lon": lon} if (lat is not None and lon is not None) else {}
    if location:
        pop = get_population_impact(lat, lon, area_km2_override=affected_area_km2)
    else:
        pop = {"estimated_affected_population": 0, "data_label": "NO LOCATION PROVIDED"}
    importance = get_importance_score(inferred_asset_type)
    nearby_critical = find_nearby_critical_facilities(lat or 0, lon or 0) if location else []
    nearby_critical_names = [
        row.get("name", row.get("type", "an unnamed facility")) for row in nearby_critical
    ]

    # --- Disaster-specific factor wiring (config.DISASTER_FACTORS) ---
    # A flood and an aircraft crash with similar raw damage % no longer score
    # identically: this looks at which disaster-specific signals (flood
    # depth/road blockage for floods; fire/smoke/debris field for crashes;
    # structural tilt/aftershock risk for earthquakes) actually show up in
    # the pooled detections for THIS disaster type, and only credits those.
    disaster_analysis = compute_disaster_conditions(disaster_type, all_detections)
    # For "generic" (no configured factors) fall back to the manual slider
    # value from the frontend; otherwise the computed, evidence-based score.
    resolved_disaster_conditions = (
        disaster_conditions if disaster_type == "generic" else disaster_analysis["disaster_conditions"]
    )

    site = {
        "site_id": case_name,
        "asset_type": inferred_asset_type,
        "disaster_type": disaster_type,
        "damage_severity": severity["severity_score"],
        "population_impact": min(10, pop["estimated_affected_population"] / 5000),
        "infrastructure_importance": importance,
        "accessibility": accessibility,
        "disaster_conditions": resolved_disaster_conditions,
        "critical_facility_impact": min(10, len(nearby_critical) * 3),
        "cascading_impact": min(10, len(nearby_critical) * 2),
        "human_impact": min(10, pop["estimated_affected_population"] / 5000),
        "time_sensitivity": min(10, severity["severity_score"]),
        "alternative_route_risk": accessibility,
        "data_confidence": severity["ai_confidence"],
    }

    priority_result = calculate_priority(site)
    site.update(priority_result)
    site["disaster_factor_analysis"] = disaster_analysis
    site["nearby_critical_facilities"] = nearby_critical_names
    site["severity_score"] = severity["severity_score"]
    # Damage severity is 0-10 internally; also expose a 0-100 version so the
    # UI/AI Assistant can show it consistently alongside priority_score (0-100)
    # without anyone re-deriving (or mis-deriving) the conversion themselves.
    site["severity_score_100"] = round(min(10.0, max(0.0, severity["severity_score"])) * 10, 1)
    site["severity_label"] = severity["severity_label"]
    site["ai_confidence"] = severity["ai_confidence"]
    site["data_confidence_pct"] = round(site["data_confidence"] * 100, 1)
    site["dominant_damage_type"] = severity["dominant_damage_type"]
    site["location"] = location
    site["preview_image_path"] = preview_image_path
    site["files_processed"] = processed_files
    site["total_frames_analyzed"] = sum(f["frames_analyzed"] for f in processed_files)
    site["image_coverage"] = {
        "avg_affected_fraction": avg_affected_fraction,
        "area_per_file_km2": area_per_file_km2,
        "surveyed_area_km2": surveyed_area_km2,
        "estimated_affected_area_km2": affected_area_km2,
    }

    damage_type = severity["dominant_damage_type"] or "structural_damage"
    site["immediate_safety"] = get_immediate_safety(damage_type, severity["severity_score"])
    site["temporary_mitigation"] = get_temporary_mitigation(damage_type)
    site["inspection_recommendation"] = get_inspection_recommendation(damage_type, severity["severity_score"])
    site["team_equipment"] = get_team_and_equipment(damage_type, severity["severity_score"], priority_result["priority_level"])
    site["reason"] = build_reason(priority_result["breakdown"], priority_result["breakdown_max"])
    site["cascading_explanation"] = build_cascading_explanation(site, nearby_critical_names)
    site["population_data"] = pop
    site["team_size"] = estimate_team_size(
        damage_type=damage_type,
        severity_score=severity["severity_score"],
        priority_level=priority_result["priority_level"],
        estimated_affected_population=pop.get("estimated_affected_population", 0),
        accessibility=accessibility,
    )

    SITE_STORE[case_name] = site
    db_service.save_site(case_name, site)
    return site


from fastapi.responses import FileResponse

@router.get("/preview-image")
def preview_image(path: str):
    """Serves an uploaded/extracted image file back to the frontend for display.
    Restricted to the uploads directory to avoid arbitrary file access."""
    import config as _config
    abs_path = os.path.abspath(path)
    uploads_root = os.path.abspath(_config.UPLOAD_DIR)
    if not abs_path.startswith(uploads_root):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(abs_path, media_type="image/jpeg")
