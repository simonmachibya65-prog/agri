import sys
sys.path.insert(0, '.')
from modules.assistant import answer, _groq_available

print("Groq available:", _groq_available())

tests = [
    ("How do I treat Apple Scab?",         "Apple___Apple_scab"),
    ("What causes Late Blight in potato?",  "Potato___Late_blight"),
    ("Best fertilizer for maize?",          None),
    ("When should I harvest rice?",         None),
    ("How to prevent fungal diseases?",     None),
]

for q, disease in tests:
    print(f"\nQ: {q}")
    ans = answer(q, disease, "en")
    print(f"A: {ans[:200]}")
    print("-" * 50)
