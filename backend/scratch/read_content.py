import json

path = "db_debug_response.json"
try:
    with open(path, "r", encoding="utf-16") as f:
        text = f.read()
except Exception:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

print("File Length:", len(text))
try:
    data = json.loads(text)
    print("Successfully parsed JSON!")
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Failed to parse JSON:", str(e))
    print("Beginning:")
    print(text[:500])
