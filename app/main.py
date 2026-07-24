from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.endpoints import router as api_router
from .core.config import settings

app = FastAPI(
    title="JSON2CNAB750 API",
    description="API para conversão e processamento de arquivos CNAB750, incluindo suporte ao PIX automático",
    version="1.0.0",
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas da API
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/api", tags=["root"])
async def api_info():
    """Informações da API (a raiz `/` serve o frontend web)."""
    return {
        "message": "Bem-vindo à API JSON2CNAB750",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ------------------------------------------------------------------ #
# Frontend web (SPA estática servida pela própria API)               #
# ------------------------------------------------------------------ #
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.is_dir():
    # Assets (CSS/JS) em /static
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
