"""Schemas Pydantic do arquivo de RETORNO CNAB750 (padrão Pix / Itaú).

O arquivo de retorno é heterogêneo: além do Header (0) e Trailer (9), pode
conter registros de detalhe de tipos diferentes, cada um com layout próprio
(documento oficial ``Layout_padrao_CNAB750_V2_1`` - leiaute retorno):

- ``1`` - Retorno de emissão, alteração e cancelamento
- ``2`` - Informações adicionais (enviado apenas no recebimento)
- ``4`` - Geração do QR Code / EMV (enviado apenas na emissão)
- ``5`` - Recebimento

Todos os registros têm 750 bytes.
"""

from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class HeaderRetorno(BaseModel):
    """Registro Header do arquivo retorno (tipo 0)."""

    tipo_registro: Literal["0"] = "0"
    codigo_retorno: str = "2"
    literal_retorno: str = "RETORNO"
    codigo_servico: str = "02"
    literal_servico: str = "PIX"
    ispb_participante: Optional[str] = None
    tipo_pessoa_recebedor: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    chave_pix: Optional[str] = None
    data_geracao: Optional[date] = None
    codigo_convenio: Optional[str] = None
    exclusivo_psp: Optional[str] = None
    nome_recebedor: Optional[str] = None
    codigos_erro: Optional[str] = None
    numero_sequencial_retorno: Optional[str] = None
    versao_arquivo: Optional[str] = None
    numero_sequencial_registro: Optional[str] = None


class RetornoTransacao(BaseModel):
    """Detalhe tipo 1 - retorno de emissão, alteração e cancelamento."""

    tipo_registro: Literal["1"] = "1"
    identificador: Optional[str] = None
    tipo_pessoa_recebedor: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    chave_pix: Optional[str] = None
    tipo_cobranca: Optional[str] = None
    codigo_movimento: Optional[str] = None
    timestamp_expiracao: Optional[str] = None
    data_vencimento: Optional[date] = None
    validade_apos_vencimento: Optional[str] = None
    valor_original: Optional[Decimal] = None
    tipo_pessoa_devedor: Optional[str] = None
    cpf_cnpj_devedor: Optional[str] = None
    nome_devedor: Optional[str] = None
    solicitacao_pagador: Optional[str] = None
    exclusivo_psp: Optional[str] = None
    data_movimento: Optional[date] = None
    codigos_erro: Optional[str] = None
    revisao: Optional[str] = None
    tarifa_cobranca: Optional[Decimal] = None
    numero_sequencial: Optional[str] = None


class RetornoInfoAdicional(BaseModel):
    """Detalhe tipo 2 - informações adicionais (recebimento)."""

    tipo_registro: Literal["2"] = "2"
    identificador: Optional[str] = None
    nome_1: Optional[str] = None
    valor_1: Optional[str] = None
    nome_2: Optional[str] = None
    valor_2: Optional[str] = None
    numero_sequencial: Optional[str] = None


class RetornoEmv(BaseModel):
    """Detalhe tipo 4 - geração do QR Code / EMV (emissão)."""

    tipo_registro: Literal["4"] = "4"
    identificador: Optional[str] = None
    chave_pix: Optional[str] = None
    codigo_movimento: Optional[str] = None
    data_movimento: Optional[date] = None
    emv_qrcode: Optional[str] = None
    location: Optional[str] = None
    numero_sequencial: Optional[str] = None


class RetornoRecebimento(BaseModel):
    """Detalhe tipo 5 - recebimento."""

    tipo_registro: Literal["5"] = "5"
    identificador: Optional[str] = None
    ispb_participante: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    chave_pix: Optional[str] = None
    tipo_cobranca: Optional[str] = None
    codigo_movimento: Optional[str] = None
    data_movimento: Optional[date] = None
    data_vencimento: Optional[date] = None
    timestamp_pagamento: Optional[str] = None
    valor_original: Optional[Decimal] = None
    valor_juros: Optional[Decimal] = None
    valor_multa: Optional[Decimal] = None
    valor_abatimento: Optional[Decimal] = None
    valor_desconto: Optional[Decimal] = None
    valor_final: Optional[Decimal] = None
    valor_pago: Optional[Decimal] = None
    tipo_pessoa_devedor: Optional[str] = None
    cpf_cnpj_devedor: Optional[str] = None
    tipo_pessoa_pagador_final: Optional[str] = None
    cpf_cnpj_pagador_final: Optional[str] = None
    nome_pagador_final: Optional[str] = None
    mensagem_pagador_final: Optional[str] = None
    codigo_liquidacao: Optional[str] = None
    end_to_end_id: Optional[str] = None
    revisao: Optional[str] = None
    exclusivo_psp: Optional[str] = None
    tarifa_cobranca: Optional[Decimal] = None
    numero_sequencial: Optional[str] = None


class TrailerRetorno(BaseModel):
    """Registro Trailer do arquivo retorno (tipo 9)."""

    tipo_registro: Literal["9"] = "9"
    codigo_retorno: str = "2"
    codigo_servico: str = "02"
    ispb: Optional[str] = None
    codigos_erro: Optional[str] = None
    valor_total: Decimal = Decimal("0")
    quantidade_detalhes: int = 0
    numero_sequencial: Optional[str] = None


RegistroRetorno = Annotated[
    Union[RetornoTransacao, RetornoInfoAdicional, RetornoEmv, RetornoRecebimento],
    Field(discriminator="tipo_registro"),
]


class ArquivoRetorno(BaseModel):
    header: HeaderRetorno
    detalhes: List[RegistroRetorno] = Field(default_factory=list)
    trailer: TrailerRetorno


# ---------------------------------------------------------------------- #
# Resumo agregado (analise de receita) — calculado em streaming, com       #
# tamanho de saida limitado (independe da quantidade de registros).        #
# ---------------------------------------------------------------------- #
class ResumoGrupo(BaseModel):
    """Sumarização de recebimentos por uma chave (data ou chave Pix)."""

    chave: str
    quantidade: int = 0
    valor_pago: Decimal = Decimal("0")
    tarifa: Decimal = Decimal("0")
    receita_liquida: Decimal = Decimal("0")


class ResumoRetorno(BaseModel):
    """Indicadores consolidados de um arquivo de retorno (registros tipo 5)."""

    ispb_participante: Optional[str] = None
    nome_recebedor: Optional[str] = None
    data_geracao: Optional[date] = None

    quantidade: int = 0
    valor_original: Decimal = Decimal("0")
    valor_juros: Decimal = Decimal("0")
    valor_multa: Decimal = Decimal("0")
    valor_desconto: Decimal = Decimal("0")
    valor_abatimento: Decimal = Decimal("0")
    receita_bruta: Decimal = Decimal("0")  # soma dos valores pagos
    tarifas: Decimal = Decimal("0")
    receita_liquida: Decimal = Decimal("0")
    ticket_medio: Decimal = Decimal("0")

    por_dia: List[ResumoGrupo] = Field(default_factory=list)
    por_chave: List[ResumoGrupo] = Field(default_factory=list)
