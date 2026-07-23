"""Schemas Pydantic do arquivo remessa CNAB750 (padrão Pix Automático / Itaú).

Os tamanhos e posições dos campos seguem o documento oficial
``Layout_padrao_CNAB750_V2_1`` (versão 2.1 - 22/02/2021), estrutura de
envio do arquivo remessa: Header (0), Detalhe (1) e Trailer (9).
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class HeaderArquivo(BaseModel):
    """Registro Header do arquivo remessa (tipo 0) - posições 001 a 750."""

    tipo_registro: str = Field("0", max_length=1)              # 001-001 9(01)
    operacao: str = Field("1", max_length=1)                   # 002-002 9(01)
    literal_remessa: str = Field("REMESSA", max_length=7)      # 003-009 X(07)
    codigo_servico: str = Field("02", max_length=2)            # 010-011 9(02)
    literal_servico: str = Field("PIX", max_length=15)         # 012-026 X(15)
    ispb_participante: str = Field(..., max_length=8)          # 027-034 X(08)
    tipo_pessoa_recebedor: str = Field(..., max_length=2)      # 035-036 9(02)
    cpf_cnpj: str = Field(..., max_length=14)                  # 037-050 9(14)
    agencia: Optional[str] = Field(None, max_length=4)         # 051-054 9(04)
    conta: Optional[str] = Field(None, max_length=20)          # 055-074 9(20)
    tipo_conta: Optional[str] = Field(None, max_length=4)      # 075-078 X(04)
    chave_pix: Optional[str] = Field(None, max_length=77)      # 079-155 X(77)
    data_geracao: date                                         # 156-163 9(08) AAAAMMDD
    codigo_convenio: Optional[str] = Field(None, max_length=30)  # 164-193 X(30)
    exclusivo_psp: Optional[str] = Field(None, max_length=60)  # 194-253 X(60)
    nome_recebedor: Optional[str] = Field(None, max_length=100)  # 254-353 X(100)
    numero_sequencial_remessa: str = Field("1", max_length=10)  # 732-741 9(10)
    versao_arquivo: str = Field("002", max_length=3)           # 742-744 9(03)
    # 745-750 9(06): derivado pelo serviço (número sequencial do registro)
    numero_sequencial_registro: str = Field("000001", max_length=6)

    @field_validator("tipo_pessoa_recebedor")
    @classmethod
    def _valida_tipo_pessoa(cls, v: str) -> str:
        if v not in ("01", "02"):
            raise ValueError("tipo_pessoa_recebedor deve ser '01' (CPF) ou '02' (CNPJ)")
        return v


class RegistroDetalhe(BaseModel):
    """Registro Detalhe do arquivo remessa (tipo 1) - posições 001 a 750."""

    tipo_registro: str = Field("1", max_length=1)              # 001-001 9(01)
    identificador: Optional[str] = Field(None, max_length=35)  # 002-036 X(35) txid
    tipo_pessoa_recebedor: str = Field(..., max_length=2)      # 037-038 9(02)
    cpf_cnpj: str = Field(..., max_length=14)                  # 039-052 9(14)
    agencia: Optional[str] = Field(None, max_length=4)         # 053-056 9(04)
    conta: Optional[str] = Field(None, max_length=20)          # 057-076 9(20)
    tipo_conta: Optional[str] = Field(None, max_length=4)      # 077-080 X(04)
    chave_pix: str = Field(..., max_length=77)                 # 081-157 X(77)
    tipo_cobranca: str = Field("1", max_length=1)              # 158-158 X(01)
    codigo_ocorrencia: str = Field("01", max_length=2)         # 159-160 9(02)
    timestamp_expiracao: Optional[str] = Field(None, max_length=14)  # 161-174 9(14)
    data_vencimento: Optional[date] = None                     # 175-182 9(08) AAAAMMDD
    validade_apos_vencimento: Optional[str] = Field(None, max_length=4)  # 183-186 9(04)
    valor_original: Decimal = Field(Decimal("0"), ge=0)        # 187-203 9(15)V9(2)
    tipo_pessoa_devedor: Optional[str] = Field(None, max_length=2)  # 204-205 9(02)
    cpf_cnpj_devedor: Optional[str] = Field(None, max_length=14)  # 206-219 9(14)
    nome_devedor: Optional[str] = Field(None, max_length=140)  # 220-359 X(140)
    solicitacao_pagador: Optional[str] = Field(None, max_length=140)  # 360-499 X(140)
    exclusivo_psp: Optional[str] = Field(None, max_length=60)  # 500-559 X(60)
    # 745-750 9(06): derivado pelo serviço
    numero_sequencial: str = Field("000002", max_length=6)

    @field_validator("tipo_cobranca")
    @classmethod
    def _valida_tipo_cobranca(cls, v: str) -> str:
        # 1 - QR Code Estático, 2 - QR Code Dinâmico (3 é exclusivo do retorno)
        if v not in ("1", "2"):
            raise ValueError("tipo_cobranca deve ser '1' (estático) ou '2' (dinâmico)")
        return v


class TrailerArquivo(BaseModel):
    """Registro Trailer do arquivo remessa (tipo 9) - posições 001 a 750.

    ``valor_total`` e ``quantidade_registros`` são derivados automaticamente
    pelo serviço a partir dos registros de detalhe; os valores informados aqui
    são ignorados na geração e apenas preenchidos na leitura de um arquivo.
    """

    tipo_registro: str = Field("9", max_length=1)              # 001-001 9(01)
    valor_total: Decimal = Field(Decimal("0"), ge=0)           # 713-729 9(15)V9(2)
    quantidade_registros: int = Field(0, ge=0)                 # 730-744 9(15)
    numero_sequencial: str = Field("000000", max_length=6)     # 745-750 9(06)


class ArquivoRemessa(BaseModel):
    header: HeaderArquivo
    transacoes: List[RegistroDetalhe] = Field(default_factory=list)
    trailer: TrailerArquivo = Field(default_factory=TrailerArquivo)


class CriarArquivoPadraoRequest(BaseModel):
    """Dados mínimos para gerar um arquivo remessa padrão (só header/trailer)."""

    nome_arquivo: str = Field(..., description="Nome do arquivo a ser gerado (sem extensão)")
    ispb_participante: str = Field(..., max_length=8, description="ISPB do PSP recebedor")
    tipo_pessoa_recebedor: str = Field(..., max_length=2, description="01=CPF, 02=CNPJ")
    cpf_cnpj: str = Field(..., max_length=14, description="CPF/CNPJ do usuário recebedor")
    chave_pix: Optional[str] = Field(None, max_length=77, description="Chave Pix do recebedor")
    nome_recebedor: Optional[str] = Field(None, max_length=100, description="Nome/razão social do recebedor")
    numero_sequencial_remessa: str = Field("1", max_length=10, description="Número sequencial da remessa")
