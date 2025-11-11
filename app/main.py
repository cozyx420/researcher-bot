from fastapi import FastAPI, Header, HTTPException
from typing import Optional, List
import logging

from .schemas import ResearchPayload, ResearchResult, Source
from .settings import settings
from .core.fetch import search_web, fetch_and_extract
from .core.text import summarize

log = logging.getLogger("researcher")
app = FastAPI(title="researcher-bot", version="0.1.0")


@app.get("/healthz")
def healthz():
    return {"ok": True, "app": settings.app_name}


def _auth(x_api_key: Optional[str]):
    if settings.inbound_token and x_api_key != settings.inbound_token:
        raise HTTPException(status_code=401, detail="invalid api key")


@app.post("/research", response_model=ResearchResult)
def research(payload: ResearchPayload, x_api_key: Optional[str] = Header(default=None)):
    _auth(x_api_key)

    # 1) Suche (fehlertolerant)
    try:
        hits = search_web(
            payload.query,
            max_results=payload.max_sources,
            allow_domains=payload.allow_domains,
        )
    except Exception as e:
        log.warning("search_web() failed: %s", e)
        hits = []

    # 2) Inhalte holen (fehlertolerant pro Quelle)
    texts: List[str] = []
    sources: List[Source] = []
    for h in hits or []:
        try:
            txt = fetch_and_extract(h["url"])
            if txt and len(txt) > 200:
                texts.append(txt)
                sources.append(Source(title=h.get("title") or "Quelle", url=h["url"], verdict="reliable"))
        except Exception as e:
            log.info("fetch/extract failed for %s: %s", h.get("url"), e)
            continue

    # 3) Zusammenfassen (fallback: einfach Query)
    joined = " ".join(texts)[:15000] if texts else ""
    summary, bullets = summarize(joined or payload.query, payload.query)

    # 4) einfache Confidence
    conf = min(0.95, 0.55 + 0.1 * min(len(sources), 4))
    return ResearchResult(summary=summary, bullets=bullets, sources=sources, confidence=conf)
