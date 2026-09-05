"""
train.py — Crop Doctor: Train + Predict + Analyze
Single script: trains YOLOv8 classification on the PlantVillage dataset,
then saves best.pt for use by the web app.

Run:
    python train.py
"""

import os
import shutil
from pathlib import Path
from ultralytics import YOLO

# ── Config ────────────────────────────────────────────────────────────────────
TRAIN_DIR  = "dataset/train/images/color"   # ImageFolder layout (class subfolders)
BASE_MODEL = "yolov8n-cls.pt"               # nano classification — fast, accurate
EPOCHS     = 50
IMG_SIZE   = 224
BATCH      = 16
PROJECT    = "runs/train"
NAME       = "crop_doctor"

# ── Knowledge Base ────────────────────────────────────────────────────────────

CAUSES = {
    "apple_scab":          ["Fungal infection (Venturia inaequalis)", "Cool wet spring weather", "Wind-dispersed spores"],
    "black_rot":           ["Fungal pathogen (Botryosphaeria)", "Warm humid conditions", "Infected mummified fruit"],
    "cedar_apple_rust":    ["Fungal spores from nearby cedar trees", "Spring wind dispersal", "Wet weather at bud break"],
    "powdery_mildew":      ["Fungal spores (Podosphaera)", "Warm dry days with cool nights", "Poor air circulation"],
    "cercospora_leaf_spot":["Fungal pathogen (Cercospora)", "High humidity with heavy dew", "Infected crop residue"],
    "common_rust":         ["Fungal pathogen (Puccinia sorghi)", "Cool temperatures + high humidity", "Wind-dispersed spores"],
    "northern_leaf_blight":["Fungal pathogen (Exserohilum)", "Moderate temps with wet weather", "Rain and wind dispersal"],
    "bacterial_spot":      ["Bacterial infection (Xanthomonas)", "Warm wet conditions", "Rain splash and contaminated tools"],
    "early_blight":        ["Fungal pathogen (Alternaria solani)", "Warm humid conditions", "Infected soil and debris"],
    "late_blight":         ["Oomycete (Phytophthora infestans)", "Cool wet weather 10–20°C", "Wind and water droplets"],
    "haunglongbing":       ["Bacterial pathogen (Candidatus Liberibacter)", "Asian citrus psyllid insect", "Year-round spread"],
    "esca":                ["Wood-rotting fungi complex", "Hot dry summers after wet winters", "Pruning wound entry"],
    "leaf_blight":         ["Fungal pathogen (Pseudocercospora)", "Warm humid late-season", "Rain splash and wind"],
    "healthy":             ["No disease detected", "Good agricultural practices", "Optimal growing conditions"],
}

TREATMENT = {
    "apple_scab":          ["Apply captan or myclobutanil fungicide", "Remove and destroy infected leaves", "Rake fallen leaves in autumn"],
    "black_rot":           ["Prune infected branches immediately", "Apply copper-based fungicide", "Remove all mummified fruit"],
    "cedar_apple_rust":    ["Apply fungicide at bud break", "Remove nearby cedar/juniper trees if possible", "Plant rust-resistant varieties"],
    "powdery_mildew":      ["Apply sulfur or neem oil spray every 7 days", "Improve air circulation by pruning", "Avoid excess nitrogen fertilizer"],
    "cercospora_leaf_spot":["Apply foliar fungicide (azoxystrobin)", "Use resistant hybrid varieties", "Rotate crops — avoid continuous maize"],
    "common_rust":         ["Apply fungicide early at first sign", "Plant certified rust-resistant seed", "Scout fields regularly from V6 stage"],
    "northern_leaf_blight":["Apply fungicide at tasseling stage", "Use resistant hybrid varieties", "Crop rotation and residue management"],
    "bacterial_spot":      ["Apply copper bactericide spray", "Remove and destroy infected tissue", "Avoid overhead irrigation"],
    "early_blight":        ["Apply chlorothalonil or mancozeb fungicide", "Remove infected lower leaves", "Crop rotation and field sanitation"],
    "late_blight":         ["Apply systemic fungicide IMMEDIATELY", "Destroy all infected plants — do not compost", "Switch to drip irrigation"],
    "haunglongbing":       ["Remove and destroy infected trees immediately", "Control psyllid with imidacloprid", "Report to agricultural authority"],
    "esca":                ["Remove and destroy infected vines — no cure", "Protect pruning wounds with fungicide paste", "Prune only in dry weather"],
    "leaf_blight":         ["Apply copper-based fungicide", "Improve canopy air circulation", "Avoid overhead irrigation"],
    "healthy":             ["Continue current crop management", "Maintain regular monitoring schedule", "Keep field sanitation practices"],
}

PREVENTION = {
    "apple_scab":          "Plant resistant varieties; rake and destroy fallen leaves",
    "black_rot":           "Remove mummified fruit; maintain good orchard sanitation",
    "cedar_apple_rust":    "Plant rust-resistant apple varieties; remove nearby cedars",
    "powdery_mildew":      "Plant resistant varieties; ensure good air circulation",
    "cercospora_leaf_spot":"Crop rotation; tillage to reduce infected residue",
    "common_rust":         "Use certified rust-resistant seed varieties",
    "northern_leaf_blight":"Crop rotation; residue management after harvest",
    "bacterial_spot":      "Use certified disease-free seed; crop rotation",
    "early_blight":        "Crop rotation; proper field sanitation",
    "late_blight":         "Use certified seeds; avoid overhead irrigation; monitor forecasts",
    "haunglongbing":       "Control psyllid populations; use certified disease-free nursery stock",
    "esca":                "Protect pruning wounds; prune in dry weather only",
    "leaf_blight":         "Improve air circulation; avoid overhead irrigation",
    "healthy":             "Maintain regular monitoring and sanitation practices",
}


def _disease_key(class_name: str) -> str:
    """Map class name to knowledge base key."""
    name = class_name.lower()
    if "healthy" in name:             return "healthy"
    if "scab" in name:                return "apple_scab"
    if "black_rot" in name:           return "black_rot"
    if "cedar" in name or "rust" in name and "common" not in name: return "cedar_apple_rust"
    if "powdery" in name:             return "powdery_mildew"
    if "cercospora" in name or "gray_leaf" in name: return "cercospora_leaf_spot"
    if "common_rust" in name:         return "common_rust"
    if "northern" in name:            return "northern_leaf_blight"
    if "bacterial" in name:           return "bacterial_spot"
    if "early_blight" in name:        return "early_blight"
    if "late_blight" in name:         return "late_blight"
    if "haunglongbing" in name or "greening" in name: return "haunglongbing"
    if "esca" in name:                return "esca"
    if "leaf_blight" in name or "isariopsis" in name: return "leaf_blight"
    return "healthy"


# ── Analyze function (Crop Doctor) ────────────────────────────────────────────

def analyze_image(image_path: str, model: YOLO = None) -> dict:
    """
    Full Crop Doctor analysis:
    Returns crop, disease, status, severity, causes, treatment, action_time.
    """
    if model is None:
        weights = "best.pt" if Path("best.pt").exists() else "yolov8n-cls.pt"
        model = YOLO(weights)

    results = model(image_path)
    top = results[0]

    # Classification result
    if hasattr(top, "probs") and top.probs is not None:
        cls_idx    = int(top.probs.top1)
        confidence = float(top.probs.top1conf)
        class_name = top.names[cls_idx]
        # Top-5
        top5_idx  = top.probs.top5
        top5_conf = top.probs.top5conf.tolist()
        alternatives = [
            {"disease": top.names[i], "confidence": round(float(c)*100, 1)}
            for i, c in zip(top5_idx, top5_conf)
        ][1:]
    else:
        if len(top.boxes) > 0:
            cls_idx    = int(top.boxes.cls[0])
            confidence = float(top.boxes.conf[0])
            class_name = top.names[cls_idx]
        else:
            class_name = "Unknown___healthy"
            confidence = 0.0
        alternatives = []

    # Parse crop and disease from class name
    if "___" in class_name:
        crop_raw, disease_raw = class_name.split("___", 1)
    else:
        crop_raw, disease_raw = class_name, "healthy"

    crop    = crop_raw.replace("_", " ").replace(",", "").title()
    disease = disease_raw.replace("_", " ").title()

    is_healthy = "healthy" in disease_raw.lower()
    status     = "Not Affected ✅" if is_healthy else "Affected ❌"

    # Severity from confidence
    if is_healthy:
        severity = "None"
        sev_icon = "🟢"
    elif confidence > 0.75:
        severity = "High"
        sev_icon = "🔴"
    elif confidence > 0.45:
        severity = "Medium"
        sev_icon = "🟡"
    else:
        severity = "Low"
        sev_icon = "🟢"

    # Action time
    action_map = {
        "High":   "Immediately (within 24 hours)",
        "Medium": "Within 2–3 days",
        "Low":    "Monitor only (if mild)",
        "None":   "No action needed",
    }

    key = _disease_key(class_name)

    return {
        "crop":         crop,
        "disease":      disease,
        "class_name":   class_name,
        "status":       status,
        "is_healthy":   is_healthy,
        "confidence":   round(confidence * 100, 1),
        "severity":     severity,
        "severity_icon":sev_icon,
        "causes":       CAUSES.get(key, ["Unknown cause"]),
        "treatment":    TREATMENT.get(key, ["Consult an agronomist"]),
        "prevention":   PREVENTION.get(key, "Regular monitoring"),
        "action_time":  action_map[severity],
        "alternatives": alternatives,
    }


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    print("=" * 60)
    print("  🌱 Crop Doctor — YOLOv8 Classification Training")
    print("=" * 60)

    if not Path(TRAIN_DIR).is_dir():
        raise FileNotFoundError(
            f"Training directory not found: {TRAIN_DIR}\n"
            "Make sure the dataset is in place."
        )

    # Count classes
    classes = [d for d in Path(TRAIN_DIR).iterdir() if d.is_dir()]
    print(f"\n📂 Found {len(classes)} classes in {TRAIN_DIR}")
    for c in sorted(classes):
        imgs = len(list(c.glob("*.jpg")) + list(c.glob("*.JPG")) + list(c.glob("*.png")))
        print(f"   {c.name}: {imgs} images")

    print(f"\n🚀 Starting training: {EPOCHS} epochs, img={IMG_SIZE}, batch={BATCH}")
    print(f"   Base model: {BASE_MODEL}\n")

    model = YOLO(BASE_MODEL)
    model.train(
        data=TRAIN_DIR,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        project=PROJECT,
        name=NAME,
        exist_ok=True,
        verbose=True,
    )

    # Copy best weights to root
    best = Path(PROJECT) / NAME / "weights" / "best.pt"
    if best.exists():
        shutil.copy(best, "best.pt")
        print(f"\n✅ Training complete! Best weights saved to: best.pt")
        print(f"   Model ready for use in the web app.")
    else:
        print(f"\n⚠️  Could not find best.pt at {best}")

    return model


# ── Quick test ────────────────────────────────────────────────────────────────

def test(image_path: str = None):
    """Quick test of the analyze function."""
    if not Path("best.pt").exists():
        print("⚠️  best.pt not found. Run train() first.")
        return

    if not image_path:
        # Use first image from dataset as test
        for cls_dir in Path(TRAIN_DIR).iterdir():
            if cls_dir.is_dir():
                imgs = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.JPG"))
                if imgs:
                    image_path = str(imgs[0])
                    break

    if not image_path:
        print("No test image found.")
        return

    print(f"\n🔍 Testing on: {image_path}")
    result = analyze_image(image_path)

    print("\n" + "=" * 50)
    print("  🩺 CROP DOCTOR RESULT")
    print("=" * 50)
    print(f"  🌿 Crop:      {result['crop']}")
    print(f"  🦠 Disease:   {result['disease']}")
    print(f"  ⚠️  Status:    {result['status']}")
    print(f"  📊 Severity:  {result['severity']} {result['severity_icon']}")
    print(f"  🎯 Confidence:{result['confidence']}%")
    print(f"\n  🤔 Causes:")
    for c in result["causes"]:
        print(f"     • {c}")
    print(f"\n  💊 Treatment:")
    for t in result["treatment"]:
        print(f"     • {t}")
    print(f"\n  ⏰ When to Act: {result['action_time']}")
    print(f"  🛡️  Prevention: {result['prevention']}")
    print("=" * 50)
    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        trained_model = train()
        print("\n🧪 Running quick test on a sample image...")
        test()
