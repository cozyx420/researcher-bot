import httpx
import re
from typing import Tuple, List, Optional
from ..settings import settings

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _naive_summary_and_bullets(text: str, max_bullets: int = 5) -> Tuple[str, List[str]]:
    sentences = _SENT_SPLIT.split(text.strip())
    if not sentences:
        return ("", [])
    summary = " ".join(sentences[:3])[:600]
    bullets = [s.strip() for s in sentences[3:3 + max_bullets] if s.strip()]
    return (summary, bullets)


def _ollama_generate(prompt: str) -> Optional[str]:
    if not settings.ollama_base_url:
        return None
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "options": {
            "temperature": settings.ollama_temperature,
        }
    }
    with httpx.Client(timeout=60) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        # Ollama streamt je nach Endpoint; /api/generate gibt standardmäßig den Volltext zurück
        data = r.json()
        return data.get("response")


def summarize(text: str, query: str) -> Tuple[str, List[str]]:
    """Erzeuge kurze Zusammenfassung + Stichpunkte (bevorzugt via Ollama, sonst naiv)."""
    # Prompt für knappe, sachliche deutsche Ausgabe
    prompt = (
        "Fasse den folgenden Text sachlich und knapp auf Deutsch zusammen. "
        "Gib zuerst 3–5 Sätze Zusammenfassung, danach 3–5 Stichpunkte. "
        "Keine Einleitung, keine Abschweifungen.\n\n"
        f"THEMA: {query}\n\nTEXT:\n{text[:5000]}"
    )

    try:
        resp = _ollama_generate(prompt)
        if resp:
            # Grobe Trennung: Zusammenfassung vs. Aufzählung
            parts = resp.strip().split("\n")
            bullets = [p.lstrip("-• ").strip() for p in parts if p.strip().startswith(("-", "•"))]
            summary_lines = [p for p in parts if p.strip() and not p.strip().startswith(("-", "•"))]
            summary = " ".join(summary_lines)[:800]
            return (summary, bullets[:5] if bullets else [])
    except Exception:
        pass

    # Fallback: naive Heuristik
    return _naive_summary_and_bullets(text)
