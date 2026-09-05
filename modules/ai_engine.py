"""modules/ai_engine.py — YOLOv8 inference engine
Only produces output when the predicted class matches one of the 35
known training labels. Any other image is rejected as unsupported.
"""
from pathlib import Path
from PIL import Image

# ── Confidence thresholds ─────────────────────────────────────────────────────
UNKNOWN_THRESHOLD = 0.30
MEDIUM_TRUST      = 0.50
HIGH_TRUST        = 0.70

# ── Labels are loaded dynamically from the model itself ───────────────────────
# This ensures KNOWN_LABELS always matches exactly what best.pt was trained on.
# Populated when _get_model() loads successfully.
KNOWN_LABELS: list = []
_KNOWN_SET:   set  = set()

# Supported crop names (for user-facing messages)
SUPPORTED_CROPS = sorted(set(
    label.split("___")[0].replace("_", " ").replace(",", "").strip()
    for label in KNOWN_LABELS
))

ORGANIC_OPTIONS = {
    "apple_scab":           "Neem oil spray every 7 days",
    "black_rot":            "Copper-based Bordeaux mixture",
    "powdery_mildew":       "Potassium bicarbonate or baking soda spray",
    "late_blight":          "Copper fungicide (preventive only)",
    "early_blight":         "Neem oil + compost tea",
    "bacterial_spot":       "Copper hydroxide spray",
    "common_rust":          "Sulfur dust at first sign",
    "leaf_blight":          "Copper oxychloride spray",
    "bacterial_leaf_blight":"Copper bactericide spray",
    "brown_spot":           "Neem-based foliar spray",
    "leaf_smut":            "Organic seed treatment",
    "leaf_scorch":          "Copper + sulfur spray",
    "wheat_rust":           "Sulfur-based fungicide",
    "wheat_powdery_mildew": "Sulfur dust or potassium bicarbonate",
    "healthy":              "No treatment needed — keep up good practices",
}

# ── Model loader (singleton) ──────────────────────────────────────────────────
_MODEL = None

def _get_model():
    global _MODEL, KNOWN_LABELS, _KNOWN_SET, SUPPORTED_CROPS
    if _MODEL is not None:
        return _MODEL
    try:
        from ultralytics import YOLO
        for p in ["best.pt", "yolov8n-cls.pt"]:
            if Path(p).exists():
                _MODEL = YOLO(p)
                # Sync labels exactly to what THIS model was trained on
                KNOWN_LABELS = list(_MODEL.names.values())
                _KNOWN_SET   = set(KNOWN_LABELS)
                SUPPORTED_CROPS = sorted(set(
                    label.split("___")[0].replace("_", " ").replace(",", "").strip()
                    for label in KNOWN_LABELS
                ))
                print(f"✅ Model loaded: {p}  ({len(KNOWN_LABELS)} classes)")
                return _MODEL
        print("⚠️  No model file found — running in demo mode")
    except Exception as e:
        print(f"⚠️  Model load error: {e}")
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def validate_image(path: str) -> bool:
    """Return True if file is a valid readable image, converting if needed."""
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


def _ensure_readable(path: str) -> str:
    """
    Ensure the image can be read by OpenCV/YOLO.
    PIL can open more formats than OpenCV — re-save as clean JPEG if needed.
    Returns the (possibly new) path to use for inference.
    """
    try:
        with Image.open(path) as img:
            # Convert to RGB (removes alpha, handles palette modes)
            rgb = img.convert("RGB")
            # Re-save as a clean JPEG so OpenCV can always read it
            clean_path = path + "_clean.jpg"
            rgb.save(clean_path, "JPEG", quality=92)
            return clean_path
    except Exception as e:
        print(f"⚠️  Could not pre-process image: {e}")
        return path


def is_known_label(class_name: str) -> bool:
    """Return True only if class_name is one of the 35 training labels."""
    return class_name in _KNOWN_SET


def identify_crop(class_name: str) -> dict:
    """Parse a known label into crop / disease components."""
    # Normalise parentheses for splitting
    clean = class_name.replace("(including_sour)", "").replace("(", "").replace(")", "")
    parts = clean.split("___")
    crop_raw = parts[0].strip()
    disease_raw = parts[1].strip() if len(parts) > 1 else "Unknown"

    # Clean up crop name
    crop = crop_raw.replace("_", " ").replace(",", "").strip()
    # Special-case crops with underscores in name
    if "Corn" in crop or "maize" in crop.lower():
        crop = "Corn (Maize)"
    if "Cherry" in crop:
        crop = "Cherry"
    if "Pepper" in crop:
        crop = "Bell Pepper"

    is_healthy = "healthy" in disease_raw.lower()
    if is_healthy:
        disease = "Healthy"
    else:
        disease = (disease_raw
                   .replace("_", " ")
                   .replace("Gray leaf spot", "Gray Leaf Spot")
                   .strip())

    return {
        "crop": crop,
        "disease": disease,
        "disease_display": f"{crop} — {disease}",
        "is_healthy": is_healthy,
        "raw": class_name,
    }


def measure_confidence(confidence: float, is_healthy: bool, class_name: str) -> dict:
    from disease_info import get_info
    info = get_info(class_name)
    severity = "None" if is_healthy else info.get("severity", "Moderate")

    if confidence >= HIGH_TRUST:
        trust = {
            "level": "High", "label": "High Confidence", "color": "#16a34a",
            "bg": "#f0fdf4", "border": "#bbf7d0", "icon": "✅",
            "pct": int(confidence * 100),
            "message": "Result is reliable — act on this diagnosis.",
        }
    elif confidence >= MEDIUM_TRUST:
        trust = {
            "level": "Medium", "label": "Medium Confidence", "color": "#d97706",
            "bg": "#fffbeb", "border": "#fde68a", "icon": "⚠️",
            "pct": int(confidence * 100),
            "message": "Likely correct — consider a second scan with a clearer photo.",
        }
    else:
        trust = {
            "level": "Low", "label": "Low Confidence", "color": "#dc2626",
            "bg": "#fef2f2", "border": "#fecaca", "icon": "❌",
            "pct": int(confidence * 100),
            "message": "Uncertain — retake photo in good lighting and try again.",
        }

    severity_color_map = {
        "Critical": "#dc2626", "High": "#ea580c",
        "Moderate": "#d97706", "Low": "#16a34a",
        "None": "#16a34a", "Unknown": "#6b7280",
    }
    return {
        "trust": trust,
        "severity": severity,
        "severity_color": severity_color_map.get(severity, "#6b7280"),
    }


def _not_supported_result(top_class: str, confidence: float) -> dict:
    """
    Return a structured 'not supported' result when the image does not
    match any of the 35 known training labels, or confidence is too low.
    """
    supported_list = ", ".join(SUPPORTED_CROPS)
    return {
        "disease":         "Not_Supported",
        "disease_display": "Not a Supported Crop",
        "crop":            "Unknown",
        "confidence":      round(confidence * 100, 1),
        "info": {
            "cause":      "Image does not match any supported crop in our database.",
            "solution":   f"Please upload a clear photo of one of these supported crops: {supported_list}.",
            "prevention": "Make sure the leaf or fruit fills most of the frame.",
            "severity":   "Unknown",
            "when":       "N/A", "who": "N/A", "how": "N/A",
        },
        "treatment": {
            "chemical": [],
            "organic":  [],
            "steps":    [
                "Ensure the photo shows a single leaf or fruit clearly.",
                "Use natural daylight — avoid dark or blurry images.",
                f"Only these crops are supported: {supported_list}.",
                "Consult your local agronomist for other crop types.",
            ],
        },
        "severity":       "Unknown",
        "severity_color": "#6b7280",
        "is_healthy":     False,
        "is_unknown":     True,
        "is_not_supported": True,
        "trust": {
            "level": "None", "label": "Not Supported", "color": "#6b7280",
            "bg": "#f9fafb", "border": "#e5e7eb", "icon": "🚫",
            "pct": int(confidence * 100),
            "message": "This image does not match any crop in our training database.",
        },
        "passes":        {"p1": round(confidence * 100, 1), "p2": 0, "p3": 0},
        "plain_summary": "Image not recognized as a supported crop. Please upload a leaf or fruit photo from a supported crop.",
        "alternatives":  [],
    }


# ── Main inference function ───────────────────────────────────────────────────

def run_inference(image_path: str) -> dict:
    from disease_info import get_info
    from knowledge_base import TREATMENT, _disease_key

    model = _get_model()

    # ── Demo mode (no model file) ─────────────────────────────────────────────
    if model is None:
        # No model loaded — return a not-supported result so the user knows
        return _not_supported_result("demo_no_model", 0.0)
    else:
        # ── Run 3-pass inference and average confidence ───────────────────────
        try:
            # Pre-process: re-save via PIL so OpenCV/YOLO can always read it
            infer_path = _ensure_readable(image_path)
            passes = []
            for _ in range(3):
                r = model(infer_path, verbose=False)
                prob = r[0].probs
                passes.append({
                    "class_name": r[0].names[int(prob.top1)],
                    "confidence": float(prob.top1conf),
                })
            # Clean up temp file
            import os as _os
            if infer_path != image_path and _os.path.exists(infer_path):
                _os.remove(infer_path)

            # Use the class from pass 1, average confidence across all 3
            class_name = passes[0]["class_name"]
            p1 = passes[0]["confidence"]
            p2 = passes[1]["confidence"]
            p3 = passes[2]["confidence"]
            confidence = (p1 + p2 + p3) / 3

        except Exception as e:
            print(f"Inference error: {e}")
            return _not_supported_result("Error", 0.0)

    # ── Gate 1: must be a known label ─────────────────────────────────────────
    if not is_known_label(class_name):
        return _not_supported_result(class_name, confidence)

    # ── Gate 2: confidence must exceed threshold ──────────────────────────────
    if confidence < UNKNOWN_THRESHOLD:
        return _not_supported_result(class_name, confidence)

    # ── Known label + sufficient confidence → produce full result ─────────────
    crop_info   = identify_crop(class_name)
    is_healthy  = crop_info["is_healthy"]
    info        = get_info(class_name)
    conf_measure = measure_confidence(confidence, is_healthy, class_name)
    key         = _disease_key(class_name)
    treatments  = TREATMENT.get(key, ["Consult a local agronomist"])

    severity_color_map = {
        "Critical": "#dc2626", "High": "#ea580c",
        "Moderate": "#d97706", "Low": "#16a34a",
        "None": "#16a34a", "Unknown": "#6b7280",
    }
    severity = info.get("severity", "Moderate") if not is_healthy else "None"

    # Split treatments into chemical vs organic
    organic_kw = ["neem", "copper", "sulfur", "organic", "natural", "bicarbonate", "compost"]
    chemical_tx = [t for t in treatments if not any(w in t.lower() for w in organic_kw)]
    organic_tx  = [t for t in treatments if     any(w in t.lower() for w in organic_kw)]
    if not organic_tx:
        organic_tx = [ORGANIC_OPTIONS.get(key, "Neem oil or copper-based spray")]

    return {
        "disease":          class_name,
        "disease_display":  crop_info["disease_display"],
        "crop":             crop_info["crop"],
        "confidence":       round(confidence * 100, 1),
        "info":             info,
        "treatment": {
            "chemical": chemical_tx,
            "organic":  organic_tx,
            "steps":    treatments,
        },
        "severity":         severity,
        "severity_color":   severity_color_map.get(severity, "#6b7280"),
        "is_healthy":       is_healthy,
        "is_unknown":       False,
        "is_not_supported": False,
        "trust":            conf_measure["trust"],
        "passes":           {
            "p1": round(p1 * 100, 1),
            "p2": round(p2 * 100, 1),
            "p3": round(p3 * 100, 1),
        },
        "plain_summary": (
            f"{'Healthy crop detected.' if is_healthy else 'Disease detected: ' + crop_info['disease_display']}. "
            f"Confidence: {round(confidence * 100, 1)}%. Severity: {severity}."
        ),
        "alternatives": [],
    }
