import urllib.request, json, os

# Load .env
for line in open('.env').readlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

KEY = os.environ.get('GEMINI_API_KEY', '')
print(f"Gemini key: {KEY[:20]}...")

if 'paste_your' in KEY:
    print("ERROR: Please paste your Gemini key in .env first")
    exit()

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={KEY}"
payload = json.dumps({
    "contents": [{"parts": [{"text": "Say exactly: Gemini is working for Smart Crop AI!"}]}],
    "generationConfig": {"maxOutputTokens": 30}
}).encode()

req = urllib.request.Request(url, data=payload,
      headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        print("SUCCESS:", data["candidates"][0]["content"]["parts"][0]["text"])
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}:", e.read().decode()[:200])
except Exception as e:
    print("ERROR:", e)
