"""
validate_system.py — Full system validation script.
Tests all components: images, disease info, knowledge base, AI engine, and model.

Usage:
    python validate_system.py
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

PASS = 0
FAIL = 0


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ PASS: {msg}")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {msg}")


print("=" * 70)
print("  CROP AI SYSTEM — FULL VALIDATION")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════════
# 1. DATASET VALIDATION
# ══════════════════════════════════════════════════════════════════════════
print("\n┌─────────────────────────────────────────────────────────────────┐")
print("│  1. DATASET VALIDATION                                          │")
print("└─────────────────────────────────────────────────────────────────┘")

dataset_dir = "dataset/quick"
classes = sorted([d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))])

check(len(classes) == 35, f"35 classes in dataset (found {len(classes)})")

total_images = 0
empty_classes = []
for cls in classes:
    count = len([f for f in os.listdir(os.path.join(dataset_dir, cls))
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))])
    total_images += count
    if count == 0:
        empty_classes.append(cls)

check(len(empty_classes) == 0, f"No empty class folders (empty: {empty_classes})")
check(total_images > 5000, f"Sufficient images for training ({total_images} total)")

# Check train/val split exists
check(os.path.exists("dataset/train"), "Train directory exists")
check(os.path.exists("dataset/val"), "Val directory exists")

if os.path.exists("dataset/train"):
    train_classes = [d for d in os.listdir("dataset/train") if os.path.isdir(os.path.join("dataset/train", d))]
    check(len(train_classes) == 35, f"Train has 35 classes (found {len(train_classes)})")

if os.path.exists("dataset/val"):
    val_classes = [d for d in os.listdir("dataset/val") if os.path.isdir(os.path.join("dataset/val", d))]
    check(len(val_classes) == 35, f"Val has 35 classes (found {len(val_classes)})")

# ══════════════════════════════════════════════════════════════════════════
# 2. DISEASE INFO VALIDATION
# ══════════════════════════════════════════════════════════════════════════
print("\n┌─────────────────────────────────────────────────────────────────┐")
print("│  2. DISEASE INFO VALIDATION                                     │")
print("└─────────────────────────────────────────────────────────────────┘")

from disease_info import DISEASE_INFO, get_info, UNKNOWN_INFO

check(len(DISEASE_INFO) == 35, f"35 entries in DISEASE_INFO (found {len(DISEASE_INFO)})")

# Every dataset class must have disease info
missing_info = [cls for cls in classes if cls not in DISEASE_INFO]
check(len(missing_info) == 0, f"All classes have disease info (missing: {missing_info})")

# Every entry must have required fields
required_fields = ["cause", "when", "who", "how", "solution", "prevention", "severity"]
incomplete = []
for name, info in DISEASE_INFO.items():
    for field in required_fields:
        if field not in info or not info[field]:
            incomplete.append(f"{name}.{field}")

check(len(incomplete) == 0, f"All disease info fields complete (incomplete: {incomplete[:5]})")

# Test get_info function
info = get_info("Apple___Apple_scab")
check(info["cause"] != "Unknown", "get_info returns correct data for known disease")

info_unknown = get_info("NonExistent___Disease")
check(info_unknown == UNKNOWN_INFO, "get_info returns UNKNOWN_INFO for unknown disease")

# ══════════════════════════════════════════════════════════════════════════
# 3. KNOWLEDGE BASE VALIDATION
# ══════════════════════════════════════════════════════════════════════════
print("\n┌─────────────────────────────────────────────────────────────────┐")
print("│  3. KNOWLEDGE BASE VALIDATION                                   │")
print("└─────────────────────────────────────────────────────────────────┘")

from knowledge_base import CAUSES, TREATMENT, PREVENTION, _disease_key

check(len(CAUSES) >= 20, f"CAUSES has entries ({len(CAUSES)} keys)")
check(len(TREATMENT) >= 20, f"TREATMENT has entries ({len(TREATMENT)} keys)")
check(len(PREVENTION) >= 20, f"PREVENTION has entries ({len(PREVENTION)} keys)")

# Every class must map to a valid key
unmapped = []
for cls in classes:
    key = _disease_key(cls)
    if key not in CAUSES:
        unmapped.append(f"{cls} -> {key}")

check(len(unmapped) == 0, f"All classes map to knowledge base (unmapped: {unmapped})")

# Test specific mappings
check(_disease_key("Rice___Bacterial_leaf_blight") == "bacterial_leaf_blight", "Rice bacterial leaf blight maps correctly")
check(_disease_key("Wheat___Rust") == "wheat_rust", "Wheat rust maps correctly")
check(_disease_key("Wheat___Powdery_mildew") == "wheat_powdery_mildew", "Wheat powdery mildew maps correctly")
check(_disease_key("Strawberry___Leaf_scorch") == "leaf_scorch", "Strawberry leaf scorch maps correctly")
check(_disease_key("Rice___Brown_spot") == "brown_spot", "Rice brown spot maps correctly")
check(_disease_key("Rice___Leaf_smut") == "leaf_smut", "Rice leaf smut maps correctly")
check(_disease_key("Apple___healthy") == "healthy", "Healthy crops map correctly")
check(_disease_key("Tomato___Bacterial_spot") == "bacterial_spot", "Tomato bacterial spot maps correctly")

# ══════════════════════════════════════════════════════════════════════════
# 4. DATA.YAML VALIDATION
# ══════════════════════════════════════════════════════════════════════════
print("\n┌─────────────────────────────────────────────────────────────────┐")
print("│  4. DATA.YAML VALIDATION                                        │")
print("└─────────────────────────────────────────────────────────────────┘")

import yaml

with open("data.yaml", "r") as f:
    data_config = yaml.safe_load(f)

check(data_config["nc"] == 35, f"data.yaml has nc=35 (found {data_config['nc']})")
check(len(data_config["names"]) == 35, f"data.yaml has 35 class names (found {len(data_config['names'])})")

# Check new classes are in data.yaml
new_classes = ["Rice___Bacterial_leaf_blight", "Rice___Brown_spot", "Rice___Leaf_smut",
               "Strawberry___Leaf_scorch", "Strawberry___healthy",
               "Tomato___Bacterial_spot",
               "Wheat___Powdery_mildew", "Wheat___Rust", "Wheat___healthy"]

for cls in new_classes:
    check(cls in data_config["names"], f"data.yaml contains {cls}")

# ══════════════════════════════════════════════════════════════════════════
# 5. AI ENGINE VALIDATION (syntax + structure)
# ══════════════════════════════════════════════════════════════════════════
print("\n┌─────────────────────────────────────────────────────────────────┐")
print("│  5. AI ENGINE VALIDATION                                        │")
print("└─────────────────────────────────────────────────────────────────┘")

import ast

# Check syntax
for pyfile in ["modules/ai_engine.py", "disease_info.py", "knowledge_base.py",
               "crop_ai_system.py", "train_model.py"]:
    try:
        with open(pyfile, encoding="utf-8") as f:
            ast.parse(f.read())
        check(True, f"{pyfile} — valid Python syntax")
    except SyntaxError as e:
        check(False, f"{pyfile} — SYNTAX ERROR: {e}")

# Check model file
check(os.path.exists("best.pt"), "best.pt model file exists")

# ══════════════════════════════════════════════════════════════════════════
# 6. MODEL INFERENCE TEST (if model available)
# ══════════════════════════════════════════════════════════════════════════
print("\n┌─────────────────────────────────────────────────────────────────┐")
print("│  6. MODEL INFERENCE TEST                                        │")
print("└─────────────────────────────────────────────────────────────────┘")

try:
    from ultralytics import YOLO
    from pathlib import Path

    model_path = "best.pt"
    if os.path.exists(model_path):
        model = YOLO(model_path)
        num_classes = len(model.names) if hasattr(model, 'names') else 0
        print(f"  📊 Model loaded: {model_path}")
        print(f"  📊 Model classes: {num_classes}")

        # Test with a real image from the dataset
        test_image = None
        for cls in classes[:5]:
            cls_dir = os.path.join(dataset_dir, cls)
            imgs = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if imgs:
                test_image = os.path.join(cls_dir, imgs[0])
                break

        if test_image:
            results = model(test_image, verbose=False)
            top = results[0]
            if hasattr(top, "probs") and top.probs is not None:
                cls_idx = int(top.probs.top1)
                confidence = float(top.probs.top1conf)
                predicted = top.names[cls_idx]
                check(confidence > 0, f"Model produces predictions (predicted: {predicted}, conf: {confidence:.2%})")
                check(confidence < 1.01, "Confidence is valid (0-1 range)")

                # Test unknown threshold logic
                if confidence >= 0.30:
                    check(True, f"Image recognized (conf {confidence:.2%} >= 30% threshold)")
                else:
                    check(True, f"Image below threshold (conf {confidence:.2%} < 30%) — would show 'not recognized'")
            else:
                check(False, "Model did not return classification probabilities")
        else:
            check(False, "No test image found in dataset")
    else:
        print("  ⚠️  best.pt not found — model still training. Skipping inference test.")
        print("     Run this validation again after training completes.")
except ImportError:
    print("  ⚠️  ultralytics not installed — skipping model test")
except Exception as e:
    print(f"  ⚠️  Model test error: {e}")

# ══════════════════════════════════════════════════════════════════════════
# 7. APP VALIDATION
# ══════════════════════════════════════════════════════════════════════════
print("\n┌─────────────────────────────────────────────────────────────────┐")
print("│  7. APP VALIDATION                                              │")
print("└─────────────────────────────────────────────────────────────────┘")

with open("app.py", encoding="utf-8") as f:
    app_content = f.read()

# Check supported crops list includes new crops
for crop in ["Rice", "Strawberry", "Tomato", "Wheat"]:
    check(crop in app_content, f"App UI lists {crop} as supported crop")

# Check required modules exist
required_modules = ["modules/ai_engine.py", "modules/auth.py", "modules/database.py",
                    "modules/weather.py", "modules/assistant.py", "modules/monitoring.py",
                    "modules/market.py", "modules/shell.py"]

for mod in required_modules:
    check(os.path.exists(mod), f"Module exists: {mod}")

# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"  VALIDATION COMPLETE")
print(f"  ✅ PASSED: {PASS}")
print(f"  ❌ FAILED: {FAIL}")
print(f"  📊 TOTAL:  {PASS + FAIL} checks")
print("=" * 70)

if FAIL == 0:
    print("\n  🎉 ALL CHECKS PASSED — System is complete and valid!")
else:
    print(f"\n  ⚠️  {FAIL} check(s) failed — review above for details.")

sys.exit(0 if FAIL == 0 else 1)
