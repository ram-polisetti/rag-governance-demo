import json, sys, urllib.request, urllib.error
sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

def embed(texts, model):
    payload = {"model": model, "input": texts}
    data = json.dumps(payload).encode()
    req = urllib.request.Request("https://ollama.com/api/embed", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    add_surrogate_to_request(req, "custom.ollama", entry_name="access_token", allowed_hosts=["ollama.com"])
    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        print(f"{model}: HTTP {e.code} {e.read().decode(errors='replace')[:200]}")
        return None
    out = read_json_response(resp)
    embs = out.get("embeddings", [])
    print(f"{model}: ok, {len(embs)} embeddings, dim={len(embs[0]) if embs else 0}")
    return embs

embed(["policy document test"], "gpt-oss:20b")
