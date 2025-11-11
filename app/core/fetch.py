import httpx
from urllib.parse import urlparse
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from ..settings import settings


def _domain_allowed(url: str, allow_domains: Optional[List[str]]) -> bool:
    if not allow_domains:
        return True
    host = urlparse(url).hostname or ""
    return any(host.endswith(d) for d in allow_domains)


def search_web(query: str, max_results: int = 5, allow_domains: Optional[List[str]] = None) -> List[Dict]:
    """Websuche (DuckDuckGo) → Liste {title, href}"""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results * 3):  # etwas Puffer, filtern wir danach
            href = r.get("href") or r.get("url")
            title = r.get("title") or ""
            if not href or not href.startswith(("http://", "https://")):
                continue
            if not _domain_allowed(href, allow_domains):
                continue
            results.append({"title": title, "url": href})
            if len(results) >= max_results:
                break
    return results


def fetch_and_extract(url: str) -> str:
    """Seite laden und lesbaren Text extrahieren (readability → Text)"""
    headers = {"User-Agent": settings.user_agent}
    with httpx.Client(timeout=settings.http_timeout, headers=headers, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    # Readability: extrahiert 'Hauptinhalt' als HTML
    doc = Document(html)
    summary_html = doc.summary(html_partial=True)

    # Text aus summary_html ziehen
    soup = BeautifulSoup(summary_html, "lxml")
    # Grober Cleanup
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text
