from datetime import date
from decimal import Decimal

from app.schemas.retorno import RetornoRecebimento
from app.services.retorno_service import RetornoService

RECORD_SIZE = 750


def _registro(campos: dict) -> str:
    """Monta um registro de 750 posições a partir de {posicao_1based: valor}."""
    buf = [" "] * RECORD_SIZE
    for inicio, valor in campos.items():
        for offset, ch in enumerate(valor):
            buf[inicio - 1 + offset] = ch
    return "".join(buf)


def _valor17(reais: str) -> str:
    cents = int((Decimal(reais) * 100))
    return str(cents).rjust(17, "0")


def _arquivo_retorno() -> str:
    header = _registro(
        {
            1: "0",
            2: "2",
            3: "RETORNO",
            10: "02",
            12: "PIX",
            27: "60701190",
            35: "02",
            37: "00012345678901",
            156: "20240319",
            254: "EMPRESA RECEBEDORA LTDA",
            732: "0000000001",
            742: "002",
            745: "000001",
        }
    )
    recebimento = _registro(
        {
            1: "5",
            2: "TXID0001",
            37: "60701190",
            45: "02",
            47: "00012345678901",
            89: "recebedor@email.com",
            166: "2",
            167: "06",
            169: "20240420",
            199: _valor17("1000.50"),
            301: _valor17("1000.50"),
            334: "01",
            336: "00098765432100",
            350: "FULANO DE TAL",
            632: "E60701190202404201200ABCDEF0001",
            745: "000002",
        }
    )
    trailer = _registro(
        {
            1: "9",
            2: "2",
            3: "02",
            5: "60701190",
            713: _valor17("1000.50"),
            730: "000000000000003",
            745: "000003",
        }
    )
    return "\r\n".join([header, recebimento, trailer])


def test_retorno_estrutura():
    resultado = RetornoService.retorno_to_json(_arquivo_retorno())

    assert resultado.header.tipo_registro == "0"
    assert resultado.header.ispb_participante == "60701190"
    assert resultado.header.nome_recebedor == "EMPRESA RECEBEDORA LTDA"
    assert resultado.header.data_geracao == date(2024, 3, 19)

    assert len(resultado.detalhes) == 1
    assert resultado.trailer.quantidade_detalhes == 3
    assert resultado.trailer.valor_total == Decimal("1000.50")


def test_retorno_detalhe_recebimento():
    resultado = RetornoService.retorno_to_json(_arquivo_retorno())
    detalhe = resultado.detalhes[0]

    assert isinstance(detalhe, RetornoRecebimento)
    assert detalhe.tipo_registro == "5"
    assert detalhe.identificador == "TXID0001"
    assert detalhe.codigo_movimento == "06"  # recebimento
    assert detalhe.data_movimento == date(2024, 4, 20)
    assert detalhe.chave_pix == "recebedor@email.com"
    assert detalhe.valor_original == Decimal("1000.50")
    assert detalhe.valor_pago == Decimal("1000.50")
    assert detalhe.nome_pagador_final == "FULANO DE TAL"
    assert detalhe.end_to_end_id == "E60701190202404201200ABCDEF0001"


def test_retorno_cada_registro_vira_json():
    resultado = RetornoService.retorno_to_json(_arquivo_retorno())
    payload = resultado.model_dump(mode="json")

    assert set(payload.keys()) == {"header", "detalhes", "trailer"}
    assert payload["detalhes"][0]["tipo_registro"] == "5"
    assert payload["detalhes"][0]["valor_pago"] == "1000.50"


def test_retorno_sem_quebra_de_linha():
    conteudo = _arquivo_retorno().replace("\r\n", "")
    resultado = RetornoService.retorno_to_json(conteudo)
    assert len(resultado.detalhes) == 1
    assert resultado.trailer.quantidade_detalhes == 3
