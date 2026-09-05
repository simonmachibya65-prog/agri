"""
Augmentation-based oversampling for minority classes.
Target: minimum 1000 images per class.
Augmentations: horizontal flip, rotation, brightness/contrast, color jitter.
Augmented images and their labels are written alongside originals.
"""

import os
import random
from PIL import Image, ImageEnhance, ImageOps
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
IMAGE_FOLDER = "dataset/train/images/color"
LABEL_FOLDER = "dataset/train/labels"
TARGET_COUNT  = 1000   # minimum images per class after oversampling
SEED          = 42
# ──────────────────────────────────────────────────────────────────────────────

random.seed(SEED)

class_dirs = sorted([
    d for d in os.listdir(IMAGE_FOLDER)
    if os.path.isdir(os.path.join(IMAGE_FOLDER, d))
])
CLASS_IDS = {name: idx for idx, name in enumerate(class_dirs)}


def augment(img: Image.Image) -> Image.Image:
    """Apply a random combination of augmentations."""
    # Horizontal flip
    if random.random() < 0.5:
        img = ImageOps.mirror(img)

    # Vertical flip
    if random.random() < 0.3:
        img = ImageOps.flip(img)

    # Rotation ±30°
    if random.random() < 0.6:
        angle = random.uniform(-30, 30)
        img = img.rotate(angle, expand=False, fillcolor=(0, 0, 0))

    # Brightness
    if random.random() < 0.5:
        factor = random.uniform(0.6, 1.4)
        img = ImageEnhance.Brightness(img).enhance(factor)

    # Contrast
    if random.random() < 0.5:
        factor = random.uniform(0.6, 1.4)
        img = ImageEnhance.Contrast(img).enhance(factor)

    # Color saturation
    if random.random() < 0.5:
        factor = random.uniform(0.6, 1.4)
        img = ImageEnhance.Color(img).enhance(factor)

    # Sharpness
    if random.random() < 0.3:
        factor = random.uniform(0.5, 2.0)
        img = ImageEnhance.Sharpness(img).enhance(factor)

    return img


def write_label(label_path: str, class_id: int):
    with open(label_path, "w") as f:
        f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")


total_new = 0

for cls_name in class_dirs:
    cls_path = os.path.join(IMAGE_FOLDER, cls_name)
    class_id = CLASS_IDS[cls_name]

    imgs = [
        f for f in os.listdir(cls_path)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
        and not f.startswith("aug_")   # skip already-augmented files on re-run
    ]
    current = len(imgs)

    if current >= TARGET_COUNT:
        print(f"  SKIP  {cls_name:<55} ({current} >= {TARGET_COUNT})")
        continue

    needed = TARGET_COUNT - current
    print(f"  AUG   {cls_name:<55} ({current} → {TARGET_COUNT}, +{needed})")

    generated = 0
    pool = imgs.copy()

    while generated < needed:
        src_name = random.choice(pool)
        src_path = os.path.join(cls_path, src_name)

        try:
            img = Image.open(src_path).convert("RGB")
        except Exception as e:
            print(f"    WARNING: could not open {src_path}: {e}")
            continue

        aug_img = augment(img)

        # Unique filename
        stem = Path(src_name).stem
        aug_filename = f"aug_{generated:05d}_{stem}.jpg"
        aug_img_path = os.path.join(cls_path, aug_filename)
        aug_lbl_path = os.path.join(LABEL_FOLDER, aug_filename.replace(".jpg", ".txt"))

        aug_img.save(aug_img_path, "JPEG", quality=90)
        write_label(aug_lbl_path, class_id)

        generated += 1
        total_new += 1

print()
print(f"Done. {total_new} augmented images created.")
print()

# ── Final count report ────────────────────────────────────────────────────────
print("=== FINAL CLASS COUNTS ===")
grand_total = 0
for cls_name in class_dirs:
    cls_path = os.path.join(IMAGE_FOLDER, cls_name)
    count = len([f for f in os.listdir(cls_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    grand_total += count
    flag = "OK" if count >= TARGET_COUNT else "LOW"
    print(f"  [{flag}] {cls_name:<55} {count}")

print(f"\nTotal images (original + augmented): {grand_total}")

# ── Verify label count matches image count ────────────────────────────────────
label_count = len([f for f in os.listdir(LABEL_FOLDER) if f.endswith(".txt")])
print(f"Total labels:                        {label_count}")
print(f"Match: {grand_total == label_count}")
