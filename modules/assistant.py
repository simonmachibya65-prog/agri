"""modules/assistant.py — AI assistant with Gemini (real AI) + rule-based fallback"""
import os, json
from pathlib import Path
from knowledge_base import CAUSES, TREATMENT, PREVENTION, _disease_key

# ── Load API keys from .env ───────────────────────────────────────────────────
def _load_env():
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_URL     = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                  f"{GEMINI_MODEL}:generateContent?key={{key}}")

# Also keep Groq as secondary fallback
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"


def _gemini_available() -> bool:
    return bool(GEMINI_API_KEY and not GEMINI_API_KEY.startswith("paste"))

def _groq_available() -> bool:
    return bool(GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"))


def _call_gemini(prompt: str, system: str = "", max_tokens: int = 400) -> str:
    """Call Google Gemini API."""
    try:
        import urllib.request
        url = GEMINI_URL.format(key=GEMINI_API_KEY)
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        payload = json.dumps({
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature":     0.6,
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return ""


def _call_groq(messages: list, max_tokens: int = 400) -> str:
    """Call Groq API."""
    try:
        import urllib.request
        payload = json.dumps({
            "model":      GROQ_MODEL,
            "messages":   messages,
            "max_tokens": max_tokens,
            "temperature":0.6,
        }).encode("utf-8")
        req = urllib.request.Request(
            GROQ_URL, data=payload,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq API error: {e}")
        return ""


def _build_system(disease: str, lang: str) -> str:
    """Build the system prompt with full context about this system."""
    disease_ctx = ""
    if disease:
        dname = disease.replace("___", " — ").replace("_", " ")
        from disease_info import get_info
        info = get_info(disease)
        disease_ctx = (
            f"\nThe farmer's last scan detected: {dname}. "
            f"Severity: {info.get('severity','Unknown')}. "
            f"Cause: {info.get('cause','')}. "
            f"Treatment: {info.get('solution','')}."
        )

    lang_instruction = (
        "Reply in Swahili — simple, clear language for farmers."
        if lang == "sw" else
        "Reply in English — simple, clear language for farmers."
    )

    return f"""You are CropAI, an expert AI assistant built into the Smart Crop AI platform — an agricultural diagnosis system for Tanzanian farmers.

About this system:
- Smart Crop AI detects crop diseases from photos using YOLOv8 deep learning
- Supports 15+ crops: Apple, Corn, Potato, Tomato, Rice, Wheat, Grape, Peach, Cherry, Pepper, Orange, Soybean, Squash, Strawberry, Blueberry
- Provides disease diagnosis, treatment plans, market prices (TSh), weather data, farm management
- Built for farmers in Tanzania and East Africa
- Designed and developed by Masalago

Your role:
- Answer ANY question — crop diseases, treatments, fertilizers, irrigation, pests, market prices, harvest timing, soil health, weather, or general farming knowledge
- Be practical, actionable, and concise — under 150 words unless more detail is truly needed
- Use simple language farmers understand
- If asked about this system, explain it accurately and positively
{disease_ctx}
{lang_instruction}"""


def answer(question: str, disease: str = None, lang: str = "en") -> str:
    """Answer using best available AI, with rule-based fallback."""
    system = _build_system(disease, lang)

    # Try Gemini first
    if _gemini_available():
        result = _call_gemini(question, system)
        if result:
            return result

    # Try Groq second
    if _groq_available():
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": question},
        ]
        result = _call_groq(messages)
        if result:
            return result

    # Fall back to rule-based
    return _rule_answer(question, disease, lang)


# ── Rule-based fallback ───────────────────────────────────────────────────────

_GREETINGS = ["hello", "hi", "hey", "good morning", "good afternoon", "habari", "hujambo"]

def _rule_answer(question: str, disease: str = None, lang: str = "en") -> str:
    q = question.lower().strip()

    if any(g in q for g in _GREETINGS):
        name = disease.replace("___", " — ").replace("_", " ") if disease else ""
        return (f"Hello! I'm your AI farming assistant. "
                f"{'I can see you are dealing with ' + name + '. ' if name else ''}"
                "Ask me anything about crop diseases, treatment, or farming advice.")

    if not disease:
        if "crop" in q and "support" in q:
            return ("I support 15+ crops including Apple, Corn, Potato, Tomato, Rice, Wheat, "
                    "Grape, Peach, Cherry, Pepper, Orange, Soybean, Squash, Strawberry, and Blueberry.")
        if "ai" in q or ("how" in q and "work" in q):
            return ("I use a YOLOv8 deep learning model trained on crop disease images. "
                    "Upload a photo of your affected leaf or fruit and I'll identify the disease.")
        return ("I'm here to help with crop disease diagnosis and farming advice. "
                "Scan a crop image first, or ask about a specific crop or disease.")

    key = _disease_key(disease)
    causes     = CAUSES.get(key, [])
    treatments = TREATMENT.get(key, [])
    prevention = PREVENTION.get(key, "Regular monitoring and good field hygiene.")
    dname      = disease.replace("___", " — ").replace("_", " ")

    if key == "healthy":
        return ("Your crop appears healthy! Continue current management practices "
                "and monitor regularly to keep it that way.")

    if any(w in q for w in ["what","which","identify","tell me","explain"]):
        return (f"{dname} is caused by: {causes[0] if causes else 'unknown pathogen'}. "
                f"It occurs under conditions of {causes[1] if len(causes)>1 else 'favourable weather'}.")

    if any(w in q for w in ["serious","severe","bad","dangerous","risk"]):
        return (f"{dname} can cause significant yield loss if untreated. "
                f"Act immediately — early treatment prevents most damage. Prevention: {prevention}")

    if any(w in q for w in ["cause","why","reason","happen"]):
        return f"Causes of {dname}: {'; '.join(causes) if causes else 'environmental factors'}."

    if any(w in q for w in ["treat","cure","fix","solution","medicine","fungicide"]):
        steps = "\n".join(f"{i+1}. {t}" for i, t in enumerate(treatments[:3]))
        return f"Treatment for {dname}:\n{steps}"

    if any(w in q for w in ["prevent","avoid","stop","protect"]):
        return f"Prevention of {dname}: {prevention}"

    if any(w in q for w in ["when","time","urgent","quickly"]):
        return (f"Act within 24–48 hours for {dname}. "
                "Early treatment is critical — delay reduces effectiveness significantly.")

    if any(w in q for w in ["organic","natural","chemical-free","bio","neem"]):
        organic = [t for t in treatments if any(w in t.lower() for w in ["neem","copper","sulfur","organic","natural"])]
        if organic:
            return f"Organic options for {dname}: " + "; ".join(organic)
        return f"For {dname}, try copper-based sprays, neem oil, or potassium bicarbonate."

    if any(w in q for w in ["who","expert","help","specialist","agronomist"]):
        return ("Contact your local agricultural extension officer or a certified agronomist. "
                "For Critical diseases, professional assessment is strongly recommended.")

    if any(w in q for w in ["where","spread","location","area"]):
        return (f"{dname} spreads through {causes[2] if len(causes)>2 else 'environmental vectors'}. "
                "Isolate affected plants and avoid working in wet fields.")

    steps = "; ".join(treatments[:2]) if treatments else "consult an agronomist"
    return (f"For {dname}: Caused by {causes[0] if causes else 'unknown'}. "
            f"Treatment: {steps}. Prevention: {prevention}")


def suggested_questions(disease: str = None, lang: str = "en") -> list:
    if not disease or _disease_key(disease) == "healthy":
        return [
            "What crops do you support?",
            "How does the AI work?",
            "How do I take a good scan photo?",
            "Best fertilizer for maize?",
            "When should I water my crops?",
        ]
    return [
        "What is this disease?",
        "How serious is this?",
        "How do I treat it?",
        "How do I prevent it?",
        "Are there organic options?",
        "When should I act?",
    ]


def w_response(disease: str, lang: str = "en", field: str = "your field") -> dict:
    from disease_info import get_info
    info  = get_info(disease)
    dname = disease.replace("___", " — ").replace("_", " ")
    key   = _disease_key(disease)
    causes     = CAUSES.get(key, [])
    treatments = TREATMENT.get(key, [])
    return {
        "what":  f"{dname}. {info.get('cause', '')}",
        "where": info.get("who", f"Affects {dname.split('—')[0].strip()} crops in {field}."),
        "when":  info.get("when", "During favourable weather conditions."),
        "why":   "; ".join(causes[:2]) if causes else info.get("cause", "Environmental factors."),
        "who":   "Contact your local agricultural extension officer for professional help.",
    }
