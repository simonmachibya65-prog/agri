import os

# Paths
image_folder = "dataset/train/images/color"
label_folder = "dataset/train/labels"
os.makedirs(label_folder, exist_ok=True)

# Assign class IDs from sorted folder names (deterministic ordering)
class_dirs = sorted([
    d for d in os.listdir(image_folder)
    if os.path.isdir(os.path.join(image_folder, d))
])

classes = {folder: idx for idx, folder in enumerate(class_dirs)}

print(f"Found {len(classes)} classes:")
for name, idx in classes.items():
    print(f"  {idx}: {name}")

# Create labels
total = 0
for folder_name, class_id in classes.items():
    folder_path = os.path.join(image_folder, folder_name)
    for img in os.listdir(folder_path):
        if img.lower().endswith((".jpg", ".jpeg", ".png")):
            label_name = os.path.splitext(img)[0] + ".txt"
            label_path = os.path.join(label_folder, label_name)
            # Full-image bounding box in YOLO format: class cx cy w h
            with open(label_path, "w") as f:
                f.write(f"{class_id} 0.5 0.5 1.0 1.0\n")
            total += 1

print(f"\nGenerated {total} label files in '{label_folder}'")
