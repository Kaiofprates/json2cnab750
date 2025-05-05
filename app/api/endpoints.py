from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse
import json
from typing import Dict, Any
from pathlib import Path
import tempfile
import os

from ..schemas.cnab750 import ArquivoRemessa, CriarArquivoPadraoRequest
from ..services.cnab750_service import CNAB750Service

router = APIRouter()

@router.post("/json-to-cnab750", response_class=PlainTextResponse)
async def converter_json_para_cnab750(arquivo: ArquivoRemessa) -> str:
    """
    Converte um JSON no formato ArquivoRemessa para um arquivo CNAB750.
    """
    try:
        return CNAB750Service.json_to_cnab750(arquivo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cnab750-to-json")
async def converter_cnab750_para_json(
    arquivo: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Converte um arquivo CNAB750 para JSON no formato ArquivoRemessa.
    """
    try:
        conteudo = await arquivo.read()
        conteudo_str = conteudo.decode("utf-8")
        
        arquivo_remessa = CNAB750Service.cnab750_to_json(conteudo_str)
        return arquivo_remessa.dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/criar-arquivo-padrao")
async def criar_arquivo_padrao(request: CriarArquivoPadraoRequest):
    """
    Cria um arquivo CNAB750 padrão sem transações.
    O arquivo será salvo na pasta 'output' do projeto.
    """
    try:
        # Gera o arquivo
        file_path = CNAB750Service.criar_arquivo_padrao(
            nome_arquivo=request.nome_arquivo,
            codigo_empresa=request.codigo_empresa,
            nome_empresa=request.nome_empresa,
            numero_banco=request.numero_banco,
            nome_banco=request.nome_banco
        )
        
        return JSONResponse(
            content={
                "message": "Arquivo criado com sucesso",
                "file_path": file_path
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 