import httpx
from urllib.parse import urlparse, parse_qs, urlsplit, unquote
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from readability import Document
from ..settings import settings


def _domain_allowed(url: str, allow_domains: Optional[List[str]]) -> bool:
    if not allow_domains:
        return True
    host = urlparse(url).hostname or ""
    return any(host.endswith(d) for d in allow_domains)


def _normalize_ecosia_href(href: str) -> Optional[str]:
    """
    Ecosia verlinkt teils direkt, teils über /redirect?url=...
    Diese Funktion gibt eine bereinigte http(s)-Ziel-URL zurück oder None.
    """
    if not href:
        return None
    if href.startswith(("http://", "https://")):
        # Direkter Link
        return href
    # Redirect-Links erkennen
    # Beispiele: https://www.ecosia.org/redirect?url=https%3A%2F%2Fexample.com%2F...
    if "ecosia.org/redirect" in href or href.startswith("/redirect"):
        qs = parse_qs(urlsplit(href).query)
        target = qs.get("url", [None])[0]
        if target and target.startswith(("http://", "https://")):
            return unquote(target)
    return None


def search_web(query: str, max_results: int = 5, allow_domains: Optional[List[str]] = None) -> List[Dict]:
    """
    Websuche via Ecosia (HTML-Seite parsen) -> Liste {title, url}
    Fällt leise auf [] zurück, wenn Ecosia blockt/fehlerschlägt.
    """
    results: List[Dict] = []
    headers = {"User-Agent": settings.user_agent}
    params = {"q": query}

    try:
        with httpx.Client(timeout=settings.http_timeout, headers=headers, follow_redirects=True) as client:
            resp = client.get(settings.ecosia_base_url, params=params)
            # Bei Anti-Bot/Rate-Limit nicht crashen:
            if resp.status_code >= 400:
                return []
            html = resp.text
    except Exception:
        return []

    soup = BeautifulSoup(html, "lxml")

    candidates = soup.select(
        "a.result-title, a.js-result-title, a[data-testid='result-title'], "
        "article a[href], div.result a[href]"
    )

    seen = set()
    for a in candidates:
        href = a.get("href")
        title = a.get_text(strip=True) or ""
        url = _normalize_ecosia_href(href)
        if not url or not url.startswith(("http://", "https://")):
            continue
        if not _domain_allowed(url, allow_domains):
            continue
        if url in seen:
            continue
        seen.add(url)
        results.append({"title": title or url, "url": url})
        if len(results) >= max_results:
            break
    return results


    # Mögliche Selektoren für Ergebnis-Links (breit gefasst, falls Ecosia das Markup ändert)
    candidates = soup.select(
        "a.result-title, a.js-result-title, a[data-testid='result-title'], "
        "article a[href], div.result a[href]"
    )

    seen = set()
    for a in candidates:
        href = a.get("href")
        title = a.get_text(strip=True) or ""

        url = _normalize_ecosia_href(href)
        if not url:
            # Manche Links sind interne Navigations-/Anker-Links → überspringen
            continue
        if not url.startswith(("http://", "https://")):
            continue
        if not _domain_allowed(url, allow_domains):
            continue
        if url in seen:
            continue

        seen.add(url)
        results.append({"title": title or url, "url": url})
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
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text
