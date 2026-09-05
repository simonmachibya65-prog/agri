import urllib.request, json

KEY = open('.env').read().split('GROQ_API_KEY=')[1].strip().split()[0]
print(f"Testing key: {KEY[:20]}...")

payload = json.dumps({
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role":"user","content":"Say: Groq is working! in one line"}],
    "max_tokens": 20
}).encode()

req = urllib.request.Request(
    "https://api.groq.com/openai/v1/chat/completions",
    data=payload,
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        print("SUCCESS:", data["choices"][0]["message"]["content"])
except Exception as e:
    print("ERROR:", e)
