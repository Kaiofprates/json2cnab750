from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date, datetime

class HeaderArquivo(BaseModel):
    codigo_registro: str = Field("0", min_length=1, max_length=1)
    codigo_remessa: str = Field("1", min_length=1, max_length=1)
    literal_remessa: str = Field("REMESSA", min_length=7, max_length=7)
    codigo_servico: str = Field("01", min_length=2, max_length=2)
    literal_servico: str = Field("COBRANCA", min_length=15, max_length=15)
    codigo_empresa: str = Field(..., min_length=1, max_length=20)
    nome_empresa: str = Field(..., min_length=1, max_length=30)
    numero_banco: str = Field(..., min_length=1, max_length=3)
    nome_banco: str = Field(..., min_length=1, max_length=15)
    data_geracao: date
    densidade_gravacao: str = Field("01600", min_length=5, max_length=5)
    literal_densidade: str = Field("BPI", min_length=3, max_length=3)
    numero_sequencial: str = Field(..., min_length=1, max_length=7)

    @validator('codigo_empresa')
    def pad_codigo_empresa(cls, v):
        return v.ljust(20)

    @validator('nome_empresa')
    def pad_nome_empresa(cls, v):
        return v.ljust(30)

    @validator('nome_banco')
    def pad_nome_banco(cls, v):
        return v.ljust(15)

    @validator('numero_sequencial')
    def pad_numero_sequencial(cls, v):
        return v.zfill(7)

class RegistroTransacao(BaseModel):
    codigo_registro: str = Field("1", min_length=1, max_length=1)
    tipo_inscricao: str = Field(..., min_length=2, max_length=2)
    numero_inscricao: str = Field(..., min_length=14, max_length=14)
    identificacao_empresa: str = Field(..., min_length=14, max_length=14)
    nosso_numero: str = Field(..., min_length=8, max_length=8)
    data_vencimento: date
    valor_titulo: float = Field(..., ge=0)
    especie_titulo: str = Field(..., min_length=2, max_length=2)
    identificacao_titulo: str = Field(..., min_length=10, max_length=10)
    nome_pagador: str = Field(..., min_length=30, max_length=30)
    endereco_pagador: str = Field(..., min_length=40, max_length=40)
    codigo_barras: Optional[str] = Field(None, min_length=44, max_length=44)
    chave_pix: Optional[str] = None

class TrailerArquivo(BaseModel):
    codigo_registro: str = Field("9", min_length=1, max_length=1)
    quantidade_registros: int
    valor_total: float
    numero_sequencial: str = Field(..., min_length=1, max_length=7)

    @validator('numero_sequencial')
    def pad_numero_sequencial(cls, v):
        return v.zfill(7)

class ArquivoRemessa(BaseModel):
    header: HeaderArquivo
    transacoes: List[RegistroTransacao]
    trailer: TrailerArquivo

class CriarArquivoPadraoRequest(BaseModel):
    nome_arquivo: str = Field(..., description="Nome do arquivo a ser gerado")
    codigo_empresa: str = Field(..., min_length=1, max_length=20, description="Código da empresa no banco")
    nome_empresa: str = Field(..., min_length=1, max_length=30, description="Nome da empresa")
    numero_banco: str = Field(..., min_length=1, max_length=3, description="Número do banco")
    nome_banco: str = Field(..., min_length=1, max_length=15, description="Nome do banco")

    @validator('codigo_empresa')
    def pad_codigo_empresa(cls, v):
        return v.ljust(20)

    @validator('nome_empresa')
    def pad_nome_empresa(cls, v):
        return v.ljust(30)

    @validator('nome_banco')
    def pad_nome_banco(cls, v):
        return v.ljust(15) 