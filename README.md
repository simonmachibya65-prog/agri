# 🌿 Crop AI Disease Detection System

An end-to-end AI system that detects crop diseases from leaf/fruit images using YOLOv8, with a FastAPI web interface and MySQL record storage.

---

## Supported Crops & Diseases (26 classes)

| Crop | Diseases |
|------|----------|
| Apple | Apple Scab, Black Rot, Cedar Apple Rust, Healthy |
| Blueberry | Healthy |
| Cherry | Powdery Mildew, Healthy |
| Corn (Maize) | Cercospora Leaf Spot, Common Rust, Northern Leaf Blight, Healthy |
| Grape | Black Rot, Esca (Black Measles), Leaf Blight, Healthy |
| Orange | Huanglongbing (Citrus Greening) |
| Peach | Bacterial Spot, Healthy |
| Bell Pepper | Bacterial Spot, Healthy |
| Potato | Early Blight, Late Blight, Healthy |
| Raspberry | Healthy |
| Soybean | Healthy |
| Squash | Powdery Mildew |

---

## Project Structure

```
crop_ai_system/
├── app.py              # FastAPI web application (main entry point)
├── train.py            # YOLOv8 model training script
├── create_labels.py    # YOLO detection label generator
├── db.py               # MySQL database helpers
├── disease_info.py     # Disease knowledge base (26 classes)
├── setup_db.py         # One-time DB initialisation
├── data.yaml           # YOLO dataset config
├── requirements.txt    # Python dependencies
├── best.pt             # Trained model weights (generated after training)
├── uploads/            # Uploaded images (auto-created)
└── dataset/
    └── train/
        └── images/
            └── color/
                └── <ClassName>/   # One folder per class
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up the database

Make sure MySQL is running, then:

```bash
python setup_db.py
```

Edit `db.py` to change the MySQL credentials if needed (default: root / no password).

### 3. Generate YOLO labels (detection mode only)

```bash
python create_labels.py
```

### 4. Train the model

```bash
python train.py
```

This trains a YOLOv8 nano classification model for 30 epochs and saves `best.pt` to the project root.

Training time depends on hardware:
- GPU (CUDA): ~10–20 minutes
- CPU only: ~1–3 hours

### 5. Run the web app

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at: **http://localhost:8000**

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Upload form (web UI) |
| POST | `/detect` | Submit image for detection |
| GET | `/history` | View detection history |
| GET | `/api/records` | JSON list of recent records |
| GET | `/health` | System health check |

---

## Configuration

| File | What to change |
|------|---------------|
| `db.py` | MySQL host, user, password |
| `train.py` | Epochs, batch size, image size, base model |
| `data.yaml` | Dataset paths and class names |

---

## Notes

- The app works without MySQL — it will skip DB saving and show a warning on the History page.
- If `best.pt` is not found, the app falls back to the base `yolov8n-cls.pt` (untrained on crop diseases).
- Always train the model before deploying for accurate results.
