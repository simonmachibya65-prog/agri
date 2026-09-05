import os
from collections import defaultdict

color_folder = "dataset/train/images/color"

print("=" * 60)
print("DATASET INSPECTION REPORT")
print("=" * 60)

if not os.path.exists(color_folder):
    print("ERROR: color folder not found")
    exit()

class_dirs = sorted([d for d in os.listdir(color_folder) if os.path.isdir(os.path.join(color_folder, d))])

print(f"\nTotal classes: {len(class_dirs)}")
print()

# Per-class image stats
print("=== CLASS BREAKDOWN ===")
total_images = 0
class_counts = {}
ext_counts = defaultdict(int)
corrupt_files = []

for cls in class_dirs:
    cls_path = os.path.join(color_folder, cls)
    files = os.listdir(cls_path)
    imgs = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
    class_counts[cls] = len(imgs)
    total_images += len(imgs)
    for f in imgs:
        ext_counts[os.path.splitext(f)[1].upper()] += 1
    # Check for non-image files
    non_imgs = [f for f in files if not f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
    if non_imgs:
        print(f"  [{cls}] has non-image files: {non_imgs[:3]}")

print(f"{'Class':<55} {'Count':>6}")
print("-" * 63)
for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
    bar = "#" * (count // 200)
    print(f"  {cls:<53} {count:>6}  {bar}")

print()
print(f"Total images: {total_images}")
print()

# Class imbalance
counts = list(class_counts.values())
max_cls = max(class_counts, key=class_counts.get)
min_cls = min(class_counts, key=class_counts.get)
avg = sum(counts) / len(counts)
print("=== CLASS BALANCE ===")
print(f"  Max: {max_cls} ({class_counts[max_cls]} images)")
print(f"  Min: {min_cls} ({class_counts[min_cls]} images)")
print(f"  Avg: {avg:.0f} images/class")
print(f"  Imbalance ratio (max/min): {class_counts[max_cls] / class_counts[min_cls]:.1f}x")

print()
print("=== FILE EXTENSIONS ===")
for ext, cnt in sorted(ext_counts.items(), key=lambda x: -x[1]):
    print(f"  {ext}: {cnt}")

print()
print("=== IMAGE SIZE SAMPLE (first image per class) ===")
try:
    from PIL import Image
    size_counts = defaultdict(int)
    for cls in class_dirs:
        cls_path = os.path.join(color_folder, cls)
        imgs = [f for f in os.listdir(cls_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if imgs:
            try:
                img_path = os.path.join(cls_path, imgs[0])
                with Image.open(img_path) as im:
                    size_counts[im.size] += 1
            except Exception as e:
                corrupt_files.append(img_path)
    print("  Unique sizes (W x H):")
    for size, cnt in sorted(size_counts.items(), key=lambda x: -x[1]):
        print(f"    {size[0]}x{size[1]}: {cnt} classes sampled")
except ImportError:
    print("  PIL not available - skipping size check")

print()
print("=== NAMING CONVENTION ===")
print("  Pattern: Plant___Condition")
plants = defaultdict(list)
for cls in class_dirs:
    if "___" in cls:
        plant, condition = cls.split("___", 1)
        plants[plant].append(condition)
    else:
        plants["UNKNOWN"].append(cls)

for plant, conditions in sorted(plants.items()):
    print(f"  {plant}:")
    for c in conditions:
        print(f"    - {c}")

print()
print("=== LABELS STATUS ===")
label_folder = "dataset/train/labels"
if os.path.exists(label_folder):
    label_files = os.listdir(label_folder)
    print(f"  Labels exist: YES ({len(label_files)} files)")
else:
    print("  Labels exist: NO - training cannot proceed without labels")

print()
print("=== SUMMARY ===")
print(f"  Classes:       {len(class_dirs)}")
print(f"  Total images:  {total_images}")
print(f"  Labels ready:  {'YES' if os.path.exists(label_folder) else 'NO'}")
print(f"  Imbalanced:    {'YES' if class_counts[max_cls] / class_counts[min_cls] > 5 else 'MODERATE'}")
