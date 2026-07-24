from datetime import date
from decimal import Decimal

from app.schemas.cnab750 import (
    ArquivoRemessa,
    HeaderArquivo,
    RegistroDetalhe,
    TrailerArquivo,
)
from app.services.cnab750_service import CNAB750Service


def _arquivo_exemplo() -> ArquivoRemessa:
    return ArquivoRemessa(
        header=HeaderArquivo(
            ispb_participante="60701190",
            tipo_pessoa_recebedor="02",
            cpf_cnpj="12345678901234",
            chave_pix="recebedor@email.com",
            nome_recebedor="EMPRESA TESTE LTDA",
            data_geracao=date(2024, 3, 19),
            numero_sequencial_remessa="1",
        ),
        transacoes=[
            RegistroDetalhe(
                identificador="TXID0001",
                tipo_pessoa_recebedor="02",
                cpf_cnpj="12345678901234",
                chave_pix="recebedor@email.com",
                tipo_cobranca="2",
                codigo_ocorrencia="01",
                data_vencimento=date(2024, 4, 19),
                valor_original=Decimal("1000.50"),
                tipo_pessoa_devedor="01",
                cpf_cnpj_devedor="98765432100",
                nome_devedor="CLIENTE TESTE",
            )
        ],
    )


def test_registros_tem_750_bytes():
    conteudo = CNAB750Service.json_to_cnab750(_arquivo_exemplo())
    linhas = conteudo.split("\r\n")

    assert len(linhas) == 3  # header + 1 detalhe + trailer
    assert [linha[0] for linha in linhas] == ["0", "1", "9"]
    assert all(len(linha) == 750 for linha in linhas)


def test_trailer_derivado():
    conteudo = CNAB750Service.json_to_cnab750(_arquivo_exemplo())
    trailer = conteudo.split("\r\n")[2]

    # valor total 713-729 e quantidade de registros 730-744 (1-based)
    assert int(trailer[712:729]) == 100050  # R$ 1000,50 em centavos
    assert int(trailer[729:744]) == 3        # header + detalhe + trailer
    assert trailer[744:750] == "000003"      # nº sequencial do registro


def test_data_geracao_no_header():
    conteudo = CNAB750Service.json_to_cnab750(_arquivo_exemplo())
    header = conteudo.split("\r\n")[0]
    # data de geração 156-163 no formato AAAAMMDD
    assert header[155:163] == "20240319"


def test_round_trip():
    original = _arquivo_exemplo()
    conteudo = CNAB750Service.json_to_cnab750(original)

    resultado = CNAB750Service.cnab750_to_json(conteudo)

    assert resultado.header.ispb_participante == "60701190"
    assert resultado.header.nome_recebedor == "EMPRESA TESTE LTDA"
    assert resultado.header.data_geracao == date(2024, 3, 19)
    assert len(resultado.transacoes) == 1
    assert resultado.transacoes[0].chave_pix == "recebedor@email.com"
    assert resultado.transacoes[0].valor_original == Decimal("1000.50")
    assert resultado.transacoes[0].data_vencimento == date(2024, 4, 19)
    assert resultado.transacoes[0].nome_devedor == "CLIENTE TESTE"
    assert resultado.trailer.quantidade_registros == 3
    assert resultado.trailer.valor_total == Decimal("1000.50")

    # a re-geração deve produzir exatamente o mesmo texto
    assert CNAB750Service.json_to_cnab750(resultado) == conteudo


def test_parse_sem_quebra_de_linha():
    conteudo = CNAB750Service.json_to_cnab750(_arquivo_exemplo())
    conteudo_sem_quebra = conteudo.replace("\r\n", "")

    resultado = CNAB750Service.cnab750_to_json(conteudo_sem_quebra)
    assert len(resultado.transacoes) == 1
    assert resultado.trailer.quantidade_registros == 3
