"""
quick_train.py — Fast training using a small subset (100 images per class).
Produces best.pt in ~15-30 minutes on CPU.
Run: python quick_train.py
"""

import shutil, random
from pathlib import Path
from ultralytics import YOLO

SRC   = Path("dataset/train/images/color")
DEST  = Path("dataset/quick")
N     = 100   # images per class for quick training

# ── Build quick dataset ───────────────────────────────────────────────────────
print("Building quick dataset...")
if DEST.exists():
    shutil.rmtree(DEST)

classes = sorted([d for d in SRC.iterdir() if d.is_dir()])
print(f"Found {len(classes)} classes")

for cls_dir in classes:
    imgs = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.JPG")) + list(cls_dir.glob("*.png"))
    sample = random.sample(imgs, min(N, len(imgs)))
    out = DEST / cls_dir.name
    out.mkdir(parents=True, exist_ok=True)
    for img in sample:
        shutil.copy(img, out / img.name)
    print(f"  {cls_dir.name}: {len(sample)} images")

total = sum(1 for _ in DEST.rglob("*.jpg")) + sum(1 for _ in DEST.rglob("*.JPG"))
print(f"\nQuick dataset: {total} images across {len(classes)} classes")

# ── Train ─────────────────────────────────────────────────────────────────────
print("\nStarting quick training (10 epochs)...")
model = YOLO("yolov8n-cls.pt")
model.train(
    data=str(DEST),
    epochs=10,
    imgsz=224,
    batch=16,
    project="runs/quick",
    name="crop_doctor",
    exist_ok=True,
    verbose=True,
)

# ── Copy best.pt to root ──────────────────────────────────────────────────────
best = Path("runs/quick/crop_doctor/weights/best.pt")
if not best.exists():
    # YOLO sometimes saves in a nested path
    for p in Path("runs").rglob("best.pt"):
        best = p
        break

if best.exists():
    shutil.copy(best, "best.pt")
    print(f"\n✅ best.pt saved! ({best})")
    print("Restart the web server to use the trained model.")
else:
    print("\n⚠️  best.pt not found after training.")
