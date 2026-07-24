from io import BytesIO
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from ..schemas.cnab750 import ArquivoRemessa, CriarArquivoPadraoRequest
from ..services.cnab750_service import CNAB750Service
from ..services.excel_service import RetornoExcelService
from ..services.retorno_service import RetornoService

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Acima deste tamanho a planilha de análise é gerada no modo AGREGADO
# (sem a aba de detalhe, uma linha por recebimento), que escala para arquivos
# enormes. Abaixo dele, gera-se a planilha detalhada com fórmulas.
# 750 bytes por registro => ~40 MB equivale a ~55 mil recebimentos.
LIMITE_DETALHE_BYTES = 40 * 1024 * 1024

router = APIRouter()


def _tamanho(arquivo: UploadFile) -> int:
    """Tamanho do upload em bytes (sem carregar o conteúdo na memória)."""
    if getattr(arquivo, "size", None) is not None:
        return arquivo.size
    arquivo.file.seek(0, 2)
    tamanho = arquivo.file.tell()
    arquivo.file.seek(0)
    return tamanho


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

    O arquivo é lido em *streaming* (blocos de 1 MiB), sem carregar o conteúdo
    inteiro na memória. A resposta, porém, contém todos os registros — para
    arquivos muito grandes, prefira ``/retorno-resumo`` (análise consolidada,
    com saída de tamanho limitado). Suporta os detalhes de retorno (tipos 1, 2,
    4 e 5) além do header (0) e trailer (9).
    """
    try:
        arquivo.file.seek(0)
        arquivo_retorno = await run_in_threadpool(
            RetornoService.retorno_to_json_stream, arquivo.file
        )
        return arquivo_retorno.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retorno-resumo")
async def converter_retorno_para_resumo(
    arquivo: UploadFile = File(...),
) -> Dict[str, Any]:
    """Lê um arquivo de RETORNO CNAB750 e devolve a análise de receita agregada.

    Calculada em um único passe, em *streaming*, com memória constante e saída
    de tamanho limitado (totais + sumarização por dia e por chave Pix). É a
    rota recomendada para renderizar a análise no site independentemente do
    tamanho do arquivo.
    """
    try:
        arquivo.file.seek(0)
        resumo = await run_in_threadpool(RetornoService.resumo_stream, arquivo.file)
        return resumo.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retorno-to-excel")
async def converter_retorno_para_excel(
    arquivo: UploadFile = File(...),
):
    """Lê um arquivo de RETORNO CNAB750 e devolve uma planilha Excel (.xlsx).

    Para arquivos até ~40 MB, gera a planilha **detalhada** (uma aba com uma
    linha por recebimento, totais em fórmulas). Acima disso, gera a planilha
    **agregada** — resumo + receita por dia + receita por chave, calculados em
    *streaming* — que escala para arquivos enormes (o Excel tem limite de
    ~1.048.576 linhas por aba, inviabilizando o detalhe completo nesses casos).
    """
    try:
        arquivo.file.seek(0)
        if _tamanho(arquivo) <= LIMITE_DETALHE_BYTES:
            planilha = await run_in_threadpool(_excel_detalhado, arquivo.file)
        else:
            planilha = await run_in_threadpool(_excel_agregado, arquivo.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    nome_saida = (arquivo.filename or "retorno").rsplit(".", 1)[0]
    headers = {
        "Content-Disposition": f'attachment; filename="analise_{nome_saida}.xlsx"'
    }
    return StreamingResponse(
        BytesIO(planilha), media_type=XLSX_MEDIA_TYPE, headers=headers
    )


def _excel_detalhado(fp) -> bytes:
    arquivo_retorno = RetornoService.retorno_to_json_stream(fp)
    return RetornoExcelService.gerar_excel(arquivo_retorno)


def _excel_agregado(fp) -> bytes:
    resumo = RetornoService.resumo_stream(fp)
    return RetornoExcelService.gerar_excel_resumo(resumo)


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
