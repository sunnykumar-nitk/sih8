"""
Handles saving uploaded images/videos, validation, and video frame extraction.
"""
import os
import uuid
import shutil
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import cv2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

MAX_FILE_SIZE_MB = 60
MAX_IMAGES_PER_BATCH = 10
MAX_VIDEOS_PER_BATCH = 10
MAX_FRAMES_PER_VIDEO = 5


def validate_file(filename: str, size_bytes: int) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"File exceeds {MAX_FILE_SIZE_MB}MB limit.")


def is_video(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in VIDEO_EXTENSIONS


def save_upload(file_obj, original_filename: str) -> str:
    """Saves an uploaded file-like object to disk and returns its path.
    Never executes uploaded content -- purely stores bytes."""
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(original_filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(config.UPLOAD_DIR, safe_name)
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file_obj, out)
    return dest_path


def extract_frames(video_path: str, max_frames: int = MAX_FRAMES_PER_VIDEO) -> list:
    """
    Samples up to `max_frames` evenly-spaced frames from a video and saves
    each as a temporary jpg. Returns a list of frame image paths.
    Caller is responsible for cleaning these up (see cleanup_frames()).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return []

    n = min(max_frames, total_frames)
    # evenly spaced frame indices, skipping the very first/last few % to avoid black intro/outro frames
    indices = [int(total_frames * (i + 1) / (n + 1)) for i in range(n)]

    frame_paths = []
    frame_dir = os.path.join(config.UPLOAD_DIR, "frames_" + uuid.uuid4().hex[:8])
    os.makedirs(frame_dir, exist_ok=True)

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        success, frame = cap.read()
        if not success:
            continue
        frame_path = os.path.join(frame_dir, f"frame_{idx}.jpg")
        cv2.imwrite(frame_path, frame)
        frame_paths.append(frame_path)

    cap.release()
    return frame_paths


def cleanup_frames(frame_paths: list) -> None:
    """Removes temporary extracted video frames (and their folder) after use."""
    if not frame_paths:
        return
    frame_dir = os.path.dirname(frame_paths[0])
    try:
        shutil.rmtree(frame_dir, ignore_errors=True)
    except Exception:
        pass
