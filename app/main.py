from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.endpoints import router as api_router

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

@app.get("/")
async def root():
    return {
        "message": "Bem-vindo à API JSON2CNAB750",
        "docs": "/docs",
        "redoc": "/redoc"
    } 