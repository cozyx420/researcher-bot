# researcher-bot

FastAPI-Service für Webrecherche: Sucht Quellen (DuckDuckGo), extrahiert lesbaren Text,
fassst zusammen (optional über Ollama) und liefert Summary, Stichpunkte und Quellen zurück.

## Quickstart (lokal)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 9000
