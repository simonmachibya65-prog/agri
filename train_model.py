"""
train_model.py — Prepare dataset and train YOLOv8 classification model.

This script:
1. Splits images from dataset/quick/ into train/val sets (80/20)
2. Trains a YOLOv8 classification model
3. Saves the best model as best.pt

Usage:
    python train_model.py
    python train_model.py --epochs 50 --imgsz 224
"""

import os
import shutil
import random
import argparse
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

SOURCE_DIR = Path("dataset/quick")
TRAIN_DIR = Path("dataset/train")
VAL_DIR = Path("dataset/val")
SPLIT_RATIO = 0.8  # 80% train, 20% val


def split_dataset():
    """Split images from dataset/quick into train/val directories."""
    print("=" * 60)
    print("📂 SPLITTING DATASET INTO TRAIN/VAL")
    print("=" * 60)

    # Clean previous splits
    if TRAIN_DIR.exists():
        shutil.rmtree(TRAIN_DIR)
    if VAL_DIR.exists():
        shutil.rmtree(VAL_DIR)

    TRAIN_DIR.mkdir(parents=True, exist_ok=True)
    VAL_DIR.mkdir(parents=True, exist_ok=True)

    total_images = 0
    total_train = 0
    total_val = 0

    classes = sorted([d for d in SOURCE_DIR.iterdir() if d.is_dir()])
    print(f"\n🌿 Found {len(classes)} classes:\n")

    for cls_dir in classes:
        cls_name = cls_dir.name
        images = [f for f in cls_dir.iterdir()
                  if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp', '.webp')]

        if not images:
            print(f"  ⚠️  {cls_name}: NO IMAGES FOUND — skipping")
            continue

        random.shuffle(images)
        split_idx = int(len(images) * SPLIT_RATIO)
        train_imgs = images[:split_idx]
        val_imgs = images[split_idx:]

        # Create class directories
        train_cls_dir = TRAIN_DIR / cls_name
        val_cls_dir = VAL_DIR / cls_name
        train_cls_dir.mkdir(parents=True, exist_ok=True)
        val_cls_dir.mkdir(parents=True, exist_ok=True)

        # Copy images
        for img in train_imgs:
            shutil.copy2(img, train_cls_dir / img.name)
        for img in val_imgs:
            shutil.copy2(img, val_cls_dir / img.name)

        total_images += len(images)
        total_train += len(train_imgs)
        total_val += len(val_imgs)
        print(f"  ✅ {cls_name}: {len(images)} images → {len(train_imgs)} train / {len(val_imgs)} val")

    print(f"\n{'=' * 60}")
    print(f"📊 TOTAL: {total_images} images → {total_train} train / {total_val} val")
    print(f"📁 Train directory: {TRAIN_DIR}")
    print(f"📁 Val directory:   {VAL_DIR}")
    print(f"{'=' * 60}\n")

    return len(classes)


def train_model(epochs=30, imgsz=224, batch=32):
    """Train YOLOv8 classification model."""
    from ultralytics import YOLO

    print("=" * 60)
    print("🚀 TRAINING YOLOV8 CLASSIFICATION MODEL")
    print("=" * 60)
    print(f"  Epochs:     {epochs}")
    print(f"  Image size: {imgsz}")
    print(f"  Batch size: {batch}")
    print(f"  Train data: {TRAIN_DIR}")
    print(f"  Val data:   {VAL_DIR}")
    print("=" * 60 + "\n")

    # Load pretrained YOLOv8 classification model
    model = YOLO("yolov8n-cls.pt")

    # Train
    results = model.train(
        data=str(TRAIN_DIR.parent),  # parent dir containing train/ and val/
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project="runs/classify",
        name="crop_disease",
        exist_ok=True,
        patience=10,
        save=True,
        verbose=True,
    )

    # Copy best model to project root
    best_model_path = Path("runs/classify/crop_disease/weights/best.pt")
    if best_model_path.exists():
        shutil.copy2(best_model_path, "best.pt")
        print(f"\n✅ Best model saved to: best.pt")
        print(f"   You can now restart the app and it will use the new model.")
    else:
        print("\n⚠️  Training completed but best.pt not found in expected location.")
        print("   Check runs/classify/crop_disease/weights/ for the model file.")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train crop disease classification model")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs (default: 30)")
    parser.add_argument("--imgsz", type=int, default=224, help="Image size for training (default: 224)")
    parser.add_argument("--batch", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--split-only", action="store_true", help="Only split dataset, don't train")
    args = parser.parse_args()

    # Step 1: Split dataset
    num_classes = split_dataset()

    if args.split_only:
        print("✅ Dataset split complete. Run without --split-only to train.")
    else:
        # Step 2: Train model
        print(f"🌿 Training on {num_classes} crop disease classes...\n")
        train_model(epochs=args.epochs, imgsz=args.imgsz, batch=args.batch)
