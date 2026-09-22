import json, sys, urllib.request, urllib.error
sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

for path, payload in [
    ("/api/embeddings", {"model": "gpt-oss:20b", "prompt": "policy document test"}),
    ("/api/embed", {"model": "nomic-embed-text", "input": ["policy document test"]}),
]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request("https://ollama.com"+path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    add_surrogate_to_request(req, "custom.ollama", entry_name="access_token", allowed_hosts=["ollama.com"])
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        out = read_json_response(resp)
        emb = out.get("embedding") or out.get("embeddings")
        n = len(emb[0]) if isinstance(emb[0], list) else len(emb)
        print(f"{path}: OK dim={n}")
    except urllib.error.HTTPError as e:
        print(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')[:160]}")
