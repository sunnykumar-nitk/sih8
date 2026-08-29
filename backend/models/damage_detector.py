"""
Damage detection adapter.

Two implementations behind one interface:
- HeuristicDamageDetector: always available, no training needed. Actually
  analyzes the uploaded image's pixels (water-color coverage, fire/smoke
  color coverage, edge/crack density via Canny) using OpenCV -- it does
  NOT read the filename. This is a legitimate stand-in for a trained
  model: real signal, real computer vision, just not deep-learning-based
  or trained on labeled disaster data yet.
- YOLODamageDetector: wraps a real Ultralytics YOLO model once your team
  has trained weights on labeled data. Swap in via config.DEMO_MODE=false.

Both return the same structured JSON shape, so nothing downstream cares
which one produced the result.

LIMITATION (be upfront about this in a demo): this heuristic detector
estimates damage from color/edge patterns, not learned features. It is a
reasonable placeholder for a hackathon prototype, not a substitute for a
model trained on real labeled disaster imagery.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os

import numpy as np
import cv2

import config


class DamageDetector(ABC):
    @abstractmethod
    def detect(self, image_path: str) -> List[Dict[str, Any]]:
        """Return a list of detection dicts:
        {
            "object_type": "building" | "road" | "bridge" | "infrastructure",
            "damage_type": "flooding" | "fire" | "debris" | "crack" | "structural_damage",
            "damage_percentage": 0-100,
            "confidence": 0.0-1.0,
            "bounding_box": [x1, y1, x2, y2],
            "source": str
        }
        """
        raise NotImplementedError


class HeuristicDamageDetector(DamageDetector):
    """
    Real pixel-based analysis (OpenCV), not filename matching, not random.
    Same image in -> same detections out, every time.

    Signals used:
      - water_pct   : share of pixels in a blue-gray/brown "water" HSV range -> flooding
      - fire_pct    : share of pixels in an orange/red/yellow "fire" HSV range -> fire
      - edge_density: share of pixels that are strong edges (Canny) -> crack / structural damage
      - dark_pct    : share of very dark, low-saturation pixels -> debris / smoke
    """

    # HSV ranges (OpenCV: H 0-179, S/V 0-255)
    WATER_HSV_LOW = (75, 20, 20)
    WATER_HSV_HIGH = (140, 255, 200)

    FIRE_HSV_LOW = (0, 90, 120)
    FIRE_HSV_HIGH = (35, 255, 255)

    def _analyze_frame(self, img: np.ndarray) -> Dict[str, float]:
        img = cv2.resize(img, (512, 512))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        total_px = img.shape[0] * img.shape[1]

        water_mask = cv2.inRange(hsv, self.WATER_HSV_LOW, self.WATER_HSV_HIGH)
        water_pct = float(np.count_nonzero(water_mask)) / total_px

        fire_mask = cv2.inRange(hsv, self.FIRE_HSV_LOW, self.FIRE_HSV_HIGH)
        fire_pct = float(np.count_nonzero(fire_mask)) / total_px

        edges = cv2.Canny(gray, 80, 180)
        edge_density = float(np.count_nonzero(edges)) / total_px

        dark_mask = (hsv[:, :, 2] < 60)
        dark_pct = float(np.count_nonzero(dark_mask)) / total_px

        return {
            "water_pct": water_pct,
            "fire_pct": fire_pct,
            "edge_density": edge_density,
            "dark_pct": dark_pct,
        }

    def _frame_to_detections(self, signals: Dict[str, float], asset_type_hint: str = None) -> List[Dict[str, Any]]:
        detections = []

        if signals["water_pct"] > 0.12:
            severity_pct = min(100, round(signals["water_pct"] * 140))
            detections.append({
                "object_type": asset_type_hint or "road",
                "damage_type": "flooding",
                "damage_percentage": severity_pct,
                "confidence": round(min(0.97, 0.55 + signals["water_pct"]), 2),
                "bounding_box": None,
                "source": "HEURISTIC_CV",
            })

        if signals["fire_pct"] > 0.03:
            severity_pct = min(100, round(signals["fire_pct"] * 400))
            detections.append({
                "object_type": asset_type_hint or "building",
                "damage_type": "fire",
                "damage_percentage": severity_pct,
                "confidence": round(min(0.97, 0.5 + signals["fire_pct"] * 3), 2),
                "bounding_box": None,
                "source": "HEURISTIC_CV",
            })

        if signals["edge_density"] > 0.09:
            # High edge fragmentation -> cracking/structural irregularity
            severity_pct = min(100, round(signals["edge_density"] * 350))
            damage_type = "structural_damage" if severity_pct > 55 else "crack"
            detections.append({
                "object_type": asset_type_hint or "building",
                "damage_type": damage_type,
                "damage_percentage": severity_pct,
                "confidence": round(min(0.95, 0.45 + signals["edge_density"] * 2), 2),
                "bounding_box": None,
                "source": "HEURISTIC_CV",
            })

        if signals["dark_pct"] > 0.20 and signals["fire_pct"] <= 0.03:
            severity_pct = min(100, round(signals["dark_pct"] * 90))
            detections.append({
                "object_type": asset_type_hint or "road",
                "damage_type": "debris",
                "damage_percentage": severity_pct,
                "confidence": round(min(0.9, 0.4 + signals["dark_pct"]), 2),
                "bounding_box": None,
                "source": "HEURISTIC_CV",
            })

        if not detections:
            # Nothing crossed a threshold -- report low-confidence "no major damage detected"
            detections.append({
                "object_type": asset_type_hint or "infrastructure",
                "damage_type": "structural_damage",
                "damage_percentage": 5,
                "confidence": 0.4,
                "bounding_box": None,
                "source": "HEURISTIC_CV",
            })

        return detections

    def detect(self, image_path: str, asset_type_hint: str = None) -> List[Dict[str, Any]]:
        img = cv2.imread(image_path)
        if img is None:
            return []
        signals = self._analyze_frame(img)
        return self._frame_to_detections(signals, asset_type_hint)

    def estimate_affected_fraction(self, image_path: str) -> float:
        """
        Returns 0.0-1.0: how much of THIS frame visually shows damage
        (water, fire, debris/dark, or heavy edge fragmentation). This is
        what lets population-affected estimates be driven by what's
        actually visible in the uploaded photos/video frames, instead of
        a fixed search radius around the pin location.

        This is a coarse coverage estimate, not object segmentation --
        documented as such. It's a legitimate signal (more visible flood
        water -> larger fraction -> larger estimated affected area), just
        not pixel-accurate.
        """
        img = cv2.imread(image_path)
        if img is None:
            return 0.0
        s = self._analyze_frame(img)
        fraction = min(1.0, s["water_pct"] + s["fire_pct"] * 2 + s["dark_pct"] * 0.5 + s["edge_density"] * 1.5)
        return round(fraction, 3)


class YOLODamageDetector(DamageDetector):
    """Real detector wrapper. Only instantiate this once trained weights exist."""

    def __init__(self, weights_path: str):
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError(
                "ultralytics is not installed. Run: pip install ultralytics"
            ) from e
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"YOLO weights not found at {weights_path}")
        self.model = YOLO(weights_path)

    def detect(self, image_path: str, asset_type_hint: str = None) -> List[Dict[str, Any]]:
        results = self.model(image_path)
        detections = []
        for r in results:
            for box in r.boxes:
                cls_name = r.names[int(box.cls[0])]
                detections.append({
                    "object_type": cls_name,
                    "damage_type": cls_name,  # refine once class taxonomy is finalized
                    "damage_percentage": None,  # requires a severity head or heuristic
                    "confidence": round(float(box.conf[0]), 2),
                    "bounding_box": [round(float(x), 1) for x in box.xyxy[0].tolist()],
                    "source": "YOLO_MODEL",
                })
        return detections


def get_detector() -> DamageDetector:
    """Factory: automatically falls back to the heuristic detector when no
    trained model is available -- the app must never crash for this reason.
    """
    if not config.DEMO_MODE and os.path.exists(config.YOLO_WEIGHTS_PATH):
        try:
            return YOLODamageDetector(config.YOLO_WEIGHTS_PATH)
        except Exception:
            pass  # fall through to heuristic
    return HeuristicDamageDetector()


# Backwards-compatible alias (older code/notebooks import MockDamageDetector)
MockDamageDetector = HeuristicDamageDetector
