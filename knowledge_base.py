"""
knowledge_base.py — Crop disease knowledge constants.
Extracted from train.py to avoid loading YOLO on import.
Used by: modules/assistant.py, modules/ai_engine.py
"""

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
    "leaf_scorch":         ["Fungal pathogen (Diplocarpon earlianum)", "Warm humid rainy weather", "Rain splash from infected debris"],
    "bacterial_leaf_blight":["Bacterium (Xanthomonas oryzae)", "Warm humid monsoon conditions", "Irrigation water and infected seed"],
    "brown_spot":          ["Fungal pathogen (Bipolaris oryzae)", "Nutrient-deficient soils", "Wind-borne conidia and infected seed"],
    "leaf_smut":           ["Fungal pathogen (Entyloma oryzae)", "Cool temperatures with high humidity", "Wind-dispersed spores from crop residue"],
    "wheat_rust":          ["Fungal pathogen (Puccinia species)", "Cool to warm humid conditions 15–25°C", "Wind-dispersed urediniospores over long distances"],
    "wheat_powdery_mildew":["Fungal pathogen (Blumeria graminis)", "Cool humid conditions with dense canopy", "Wind-dispersed conidia in heavily fertilized crops"],
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
    "leaf_scorch":         ["Apply captan or thiram fungicide", "Remove and destroy infected leaves", "Improve air circulation between plants"],
    "bacterial_leaf_blight":["Drain fields to reduce humidity", "Apply copper bactericides", "Remove and burn infected plants"],
    "brown_spot":          ["Apply mancozeb or propiconazole fungicide", "Improve soil fertility with potassium and silicon", "Use certified healthy seed"],
    "leaf_smut":           ["Apply propiconazole or carbendazim at early symptoms", "Remove infected leaves from field", "Maintain balanced nitrogen fertilization"],
    "wheat_rust":          ["Apply triazole or strobilurin fungicide at first sign", "Use resistant cultivars", "Remove volunteer wheat plants"],
    "wheat_powdery_mildew":["Apply triadimefon or propiconazole fungicide", "Reduce nitrogen application", "Ensure proper plant spacing"],
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
    "leaf_scorch":         "Use resistant varieties; avoid overhead irrigation; remove old leaf debris",
    "bacterial_leaf_blight":"Use resistant varieties (IRBB lines); balanced fertilization; use clean seed",
    "brown_spot":          "Use certified healthy seed; balanced fertilization; proper water management",
    "leaf_smut":           "Use resistant varieties; field sanitation; balanced nitrogen; crop rotation",
    "wheat_rust":          "Plant rust-resistant cultivars; early planting; remove volunteer wheat",
    "wheat_powdery_mildew":"Use resistant varieties; avoid excessive nitrogen; proper plant spacing",
    "healthy":             "Maintain regular monitoring and sanitation practices",
}


def _disease_key(class_name: str) -> str:
    """Map class name to knowledge base key."""
    name = class_name.lower()
    if "healthy" in name:                                          return "healthy"
    if "scab" in name:                                             return "apple_scab"
    if "black_rot" in name:                                        return "black_rot"
    if "cedar" in name:                                            return "cedar_apple_rust"
    if "leaf_scorch" in name:                                      return "leaf_scorch"
    if "bacterial_leaf_blight" in name:                             return "bacterial_leaf_blight"
    if "brown_spot" in name:                                       return "brown_spot"
    if "leaf_smut" in name:                                        return "leaf_smut"
    if "wheat" in name and "rust" in name:                         return "wheat_rust"
    if "wheat" in name and "powdery" in name:                      return "wheat_powdery_mildew"
    if "powdery" in name:                                          return "powdery_mildew"
    if "cercospora" in name or "gray_leaf" in name:                return "cercospora_leaf_spot"
    if "common_rust" in name:                                      return "common_rust"
    if "rust" in name:                                             return "common_rust"
    if "northern" in name:                                         return "northern_leaf_blight"
    if "bacterial" in name:                                        return "bacterial_spot"
    if "early_blight" in name:                                     return "early_blight"
    if "late_blight" in name:                                      return "late_blight"
    if "haunglongbing" in name or "greening" in name:              return "haunglongbing"
    if "esca" in name:                                             return "esca"
    if "leaf_blight" in name or "isariopsis" in name:              return "leaf_blight"
    return "healthy"
