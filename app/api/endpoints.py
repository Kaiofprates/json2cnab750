from io import BytesIO
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from ..schemas.cnab750 import ArquivoRemessa, CriarArquivoPadraoRequest
from ..services.cnab750_service import CNAB750Service
from ..services.excel_service import RetornoExcelService
from ..services.retorno_service import RetornoService

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

router = APIRouter()


@router.post("/json-to-cnab750", response_class=PlainTextResponse)
async def converter_json_para_cnab750(arquivo: ArquivoRemessa) -> str:
    """Converte um JSON no formato ArquivoRemessa para um arquivo CNAB750."""
    try:
        return CNAB750Service.json_to_cnab750(arquivo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cnab750-to-json")
async def converter_cnab750_para_json(
    arquivo: UploadFile = File(...),
) -> Dict[str, Any]:
    """Converte um arquivo CNAB750 para JSON no formato ArquivoRemessa."""
    try:
        conteudo = await arquivo.read()
        conteudo_str = conteudo.decode("utf-8")
        arquivo_remessa = CNAB750Service.cnab750_to_json(conteudo_str)
        return arquivo_remessa.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retorno-to-json")
async def converter_retorno_para_json(
    arquivo: UploadFile = File(...),
) -> Dict[str, Any]:
    """Lê um arquivo de RETORNO CNAB750 e converte cada registro em JSON.

    Suporta os registros de detalhe de retorno (tipos 1, 2, 4 e 5) além do
    header (0) e trailer (9). Cada detalhe traz o campo ``tipo_registro``
    identificando o seu tipo.
    """
    try:
        conteudo = await arquivo.read()
        conteudo_str = conteudo.decode("utf-8")
        arquivo_retorno = RetornoService.retorno_to_json(conteudo_str)
        return arquivo_retorno.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retorno-to-excel")
async def converter_retorno_para_excel(
    arquivo: UploadFile = File(...),
):
    """Lê um arquivo de RETORNO CNAB750 e devolve uma planilha Excel (.xlsx).

    A planilha traz a análise dos recebimentos com sumarização de receita
    (resumo consolidado, detalhe, receita por dia e por chave Pix).
    """
    try:
        conteudo = await arquivo.read()
        conteudo_str = conteudo.decode("utf-8")
        arquivo_retorno = RetornoService.retorno_to_json(conteudo_str)
        planilha = RetornoExcelService.gerar_excel(arquivo_retorno)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    nome_saida = (arquivo.filename or "retorno").rsplit(".", 1)[0]
    headers = {
        "Content-Disposition": f'attachment; filename="analise_{nome_saida}.xlsx"'
    }
    return StreamingResponse(
        BytesIO(planilha), media_type=XLSX_MEDIA_TYPE, headers=headers
    )


@router.post("/criar-arquivo-padrao")
async def criar_arquivo_padrao(request: CriarArquivoPadraoRequest):
    """Cria um arquivo CNAB750 padrão (header e trailer) na pasta 'output'."""
    try:
        file_path = CNAB750Service.criar_arquivo_padrao(
            nome_arquivo=request.nome_arquivo,
            ispb_participante=request.ispb_participante,
            tipo_pessoa_recebedor=request.tipo_pessoa_recebedor,
            cpf_cnpj=request.cpf_cnpj,
            chave_pix=request.chave_pix,
            nome_recebedor=request.nome_recebedor,
            numero_sequencial_remessa=request.numero_sequencial_remessa,
        )
        return JSONResponse(
            content={"message": "Arquivo criado com sucesso", "file_path": file_path}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
