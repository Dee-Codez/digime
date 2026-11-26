import json
import urllib.request


def _ollama_generate(base_url: str, model: str, prompt: str) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read()).get("response", "")


def answer(question: str, results: list[dict], ollama_model: str, ollama_base_url: str):
    context = "\n\n".join(
        f"[{r.get('source')} | {r.get('ts')}] {r.get('title')}\n{r.get('text')}"
        for r in results
    )

    if ollama_model:
        prompt = (
            "You are an assistant with access to a person's private memory archive "
            "(emails, YouTube watch history, search activity, browsing history). "
            "Answer the question using ONLY the provided context. If the context is "
            "insufficient, say so. Do not invent facts.\n\n"
            f"CONTEXT:\n{context}\n\nQUESTION: {question}\nANSWER:"
        )
        return _ollama_generate(ollama_base_url, ollama_model, prompt)

    lines = [f"Retrieved {len(results)} relevant memories (no LLM configured — showing raw matches):\n"]
    for r in results:
        lines.append(f"- [{r.get('source')}] {r.get('title')}  (score={r.get('score', 0):.4f})")
        if r.get("url"):
            lines.append(f"  {r['url']}")
        if r.get("ts"):
            lines.append(f"  {r['ts']}")
        lines.append(f"  {(r.get('text') or '')[:300]}")
        lines.append("")
    return "\n".join(lines)
