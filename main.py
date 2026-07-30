"""LeadDesk — CRM de pipeline comercial com prospecção acoplada.

Uma única aplicação FastAPI expõe os dois módulos:

- ``crm/``          leads, pipeline de 8 etapas, interações, follow-up agendado
- ``prospecting/``  prospects, métricas semanais, conversão em lead
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from crm.database import Base, engine
from crm.jobs import followup_job
from crm.routers import interactions, leads
from crm.scheduler import start as start_scheduler, stop as stop_scheduler
from prospecting.models import Prospect  # noqa: F401 — registra a tabela no metadata
from prospecting.routers import prospects

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="LeadDesk",
    description="CRM de pipeline comercial com prospecção acoplada",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(leads.router)
app.include_router(interactions.router)
app.include_router(prospects.router)


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}


@app.post("/jobs/followup", tags=["jobs"])
def run_followup_now():
    """Dispara o job de follow-up manualmente, fora do horário agendado."""
    followup_job()
    return {"status": "executado"}


# --- interface web -----------------------------------------------------------
# HTML/CSS/JS sem build, servido pela própria API. Montado depois dos routers,
# então nenhuma rota de negócio é sombreada por um arquivo de mesmo nome.

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    pagina = STATIC_DIR / "index.html"
    if not pagina.is_file():
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Interface ainda não construída.",
                "api": "/docs",
            },
        )
    return FileResponse(pagina)
