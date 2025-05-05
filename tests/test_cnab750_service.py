import pytest
from datetime import date
from app.schemas.cnab750 import ArquivoRemessa, HeaderArquivo, RegistroTransacao, TrailerArquivo
from app.services.cnab750_service import CNAB750Service

def test_json_to_cnab750():
    # Arrange
    arquivo = ArquivoRemessa(
        header=HeaderArquivo(
            codigo_registro="0",
            codigo_remessa="1",
            literal_remessa="REMESSA",
            codigo_servico="01",
            literal_servico="COBRANCA",
            codigo_empresa="12345678901234567890",
            nome_empresa="EMPRESA TESTE LTDA",
            numero_banco="341",
            nome_banco="BANCO ITAU SA",
            data_geracao=date(2024, 3, 19),
            densidade_gravacao="01600",
            literal_densidade="BPI",
            numero_sequencial="0000001"
        ),
        transacoes=[
            RegistroTransacao(
                codigo_registro="1",
                tipo_inscricao="02",
                numero_inscricao="12345678901234",
                identificacao_empresa="12345678901234",
                nosso_numero="12345678",
                data_vencimento=date(2024, 4, 19),
                valor_titulo=1000.50,
                especie_titulo="01",
                identificacao_titulo="FAT123456",
                nome_pagador="CLIENTE TESTE",
                endereco_pagador="RUA TESTE, 123 - CENTRO",
                chave_pix="cliente@email.com"
            )
        ],
        trailer=TrailerArquivo(
            codigo_registro="9",
            quantidade_registros=1,
            valor_total=1000.50,
            numero_sequencial="0000002"
        )
    )
    
    # Act
    resultado = CNAB750Service.json_to_cnab750(arquivo)
    linhas = resultado.split("\r\n")
    
    # Assert
    assert len(linhas) == 3  # Header + 1 Transação + Trailer
    assert linhas[0][0] == "0"  # Header
    assert linhas[1][0] == "1"  # Transação
    assert linhas[2][0] == "9"  # Trailer
    assert len(linhas[0]) == 750  # Tamanho padrão CNAB750
    assert len(linhas[1]) == 750
    assert len(linhas[2]) == 750

def test_cnab750_to_json():
    # Arrange
    conteudo = (
        "01REMESSA01COBRANCA      12345678901234567890EMPRESA TESTE LTDA           341BANCO ITAU SA  190324016000BPI" + " " * 642 + "0000001\r\n"
        "102123456789012341234567890123412345678190424000000100050011234567890CLIENTE TESTE                    RUA TESTE, 123 - CENTRO              cliente@email.com" + " " * 559 + "1234567\r\n"
        "9000001000000100050" + " " * 723 + "0000002"
    )
    
    # Act
    resultado = CNAB750Service.cnab750_to_json(conteudo)
    
    # Assert
    assert isinstance(resultado, ArquivoRemessa)
    assert resultado.header.codigo_registro == "0"
    assert resultado.header.nome_empresa.strip() == "EMPRESA TESTE LTDA"
    assert len(resultado.transacoes) == 1
    assert resultado.transacoes[0].valor_titulo == 1000.50
    assert resultado.trailer.quantidade_registros == 1
    assert resultado.trailer.valor_total == 1000.50

def test_json_to_cnab750_with_pix():
    # Arrange
    transacao = RegistroTransacao(
        codigo_registro="1",
        tipo_inscricao="02",
        numero_inscricao="12345678901234",
        identificacao_empresa="12345678901234",
        nosso_numero="12345678",
        data_vencimento=date(2024, 4, 19),
        valor_titulo=1000.50,
        especie_titulo="01",
        identificacao_titulo="FAT123456",
        nome_pagador="CLIENTE TESTE",
        endereco_pagador="RUA TESTE, 123 - CENTRO",
        chave_pix="cliente@email.com"
    )
    
    # Act
    linha = CNAB750Service._formatar_transacao(transacao)
    
    # Assert
    assert len(linha) == 750
    assert linha[146:190].strip() == "cliente@email.com"  # Posição da chave PIX

def test_json_to_cnab750_with_codigo_barras():
    # Arrange
    transacao = RegistroTransacao(
        codigo_registro="1",
        tipo_inscricao="02",
        numero_inscricao="12345678901234",
        identificacao_empresa="12345678901234",
        nosso_numero="12345678",
        data_vencimento=date(2024, 4, 19),
        valor_titulo=1000.50,
        especie_titulo="01",
        identificacao_titulo="FAT123456",
        nome_pagador="CLIENTE TESTE",
        endereco_pagador="RUA TESTE, 123 - CENTRO",
        codigo_barras="12345678901234567890123456789012345678901234"
    )
    
    # Act
    linha = CNAB750Service._formatar_transacao(transacao)
    
    # Assert
    assert len(linha) == 750
    assert linha[146:190].strip() == "12345678901234567890123456789012345678901234"  # Posição do código de barras 