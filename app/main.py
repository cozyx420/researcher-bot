import uuid
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from .schemas import TaskRequest, TaskResponse, StepResult, ResearchPayload
from .settings import settings
from .clients.researcher import ResearcherClient

app = FastAPI(title="manager-bot", version="0.1.0")

# UI statisch bereitstellen (Ordner "ui")
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")


@app.get("/")
async def root():
    # Startseite zeigt die UI
    return FileResponse("ui/index.html")


@app.get("/healthz")
async def healthz():
    return {"ok": True, "app": settings.app_name}


async def _check_auth(x_api_key: Optional[str]):
    """Einfacher Header-Token-Check für eingehende Requests."""
    if settings.inbound_token and x_api_key != settings.inbound_token:
        raise HTTPException(status_code=401, detail="invalid api key")


@app.post("/task", response_model=TaskResponse)
async def run_task(req: TaskRequest, x_api_key: Optional[str] = Header(default=None)):
    await _check_auth(x_api_key)

    task_id = str(uuid.uuid4())
    steps: List[StepResult] = []

    # Schritt 1: (optional) Recherche
    if req.intent in ("research", "mixed"):
        researcher = ResearcherClient(settings.researcher_url)
        payload = ResearchPayload(
            query=req.task,
            focus=(req.params or {}).get("focus"),
            max_sources=(req.params or {}).get("max_sources", 5),
            allow_domains=(req.params or {}).get("allow_domains"),
        )
        try:
            result = await researcher.research(payload)
            if result is None:
                steps.append(
                    StepResult(
                        name="research",
                        ok=False,
                        error="researcher_url_not_configured",
                    )
                )
            else:
                steps.append(StepResult(name="research", ok=True, data=result.dict()))
        except Exception as e:
            steps.append(StepResult(name="research", ok=False, error=str(e)))
    else:
        steps.append(StepResult(name="noop", ok=True, data={"note": "no research step required"}))

    # Konsolidierung in Markdown
    md_lines = [f"### Ergebnis für Task `{req.task}`"]
    for s in steps:
        if s.ok and s.data and "summary" in s.data:
            md_lines.append("\n**Zusammenfassung:**\n")
            md_lines.append(str(s.data["summary"]))
        if s.ok and s.data and "bullets" in s.data:
            md_lines.append("\n**Punkte:**")
            for b in s.data.get("bullets", []):
                md_lines.append(f"- {b}")
        if s.ok and s.data and "sources" in s.data:
            md_lines.append("\n**Quellen:**")
            for src in s.data.get("sources", []):
                title = src.get("title")
                url = src.get("url")
                verdict = src.get("verdict", "")
                md_lines.append(f"- [{title}]({url}) · {verdict}")
        if s.error:
            md_lines.append(f"\n**Fehler in Schritt {s.name}:** {s.error}")

    return TaskResponse(task_id=task_id, steps=steps, result_markdown="\n".join(md_lines))
