"""Conversão entre JSON (ArquivoRemessa) e o texto posicional CNAB750.

O layout posicional segue o documento oficial ``Layout_padrao_CNAB750_V2_1``
(estrutura de envio do arquivo remessa: Header 0, Detalhe 1 e Trailer 9).
Cada registro tem exatamente 750 bytes.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from ..schemas.cnab750 import (
    ArquivoRemessa,
    HeaderArquivo,
    RegistroDetalhe,
    TrailerArquivo,
)

RECORD_SIZE = 750


# ---------------------------------------------------------------------------
# Formatação de campos
# ---------------------------------------------------------------------------
def _alpha(value: Optional[object], length: int) -> str:
    """Campo alfanumérico: alinhado à esquerda e completado com espaços."""
    text = "" if value is None else str(value)
    return text[:length].ljust(length)


def _num(value: Optional[object], length: int) -> str:
    """Campo numérico: apenas dígitos, alinhado à direita com zeros à esquerda."""
    if value is None:
        digits = ""
    else:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits[-length:].rjust(length, "0")


def _data(value: Optional[date], length: int = 8) -> str:
    """Data no formato AAAAMMDD (zeros quando ausente)."""
    if value is None:
        return "0" * length
    return value.strftime("%Y%m%d")


def _valor(value: Optional[object], length: int = 17) -> str:
    """Valor monetário 9(15)V9(2): duas casas decimais implícitas."""
    if value is None:
        value = 0
    cents = (Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return str(int(cents)).rjust(length, "0")[-length:]


def _assert_size(linha: str, nome: str) -> str:
    if len(linha) != RECORD_SIZE:
        raise ValueError(
            f"Registro '{nome}' com {len(linha)} bytes (esperado {RECORD_SIZE})."
        )
    return linha


# ---------------------------------------------------------------------------
# Parsing de campos
# ---------------------------------------------------------------------------
def _texto(bruto: str) -> Optional[str]:
    valor = bruto.strip()
    return valor or None


def _parse_data(bruto: str) -> Optional[date]:
    valor = bruto.strip()
    if not valor or valor == "0" * len(bruto):
        return None
    return datetime.strptime(valor, "%Y%m%d").date()


def _parse_valor(bruto: str) -> Decimal:
    valor = bruto.strip() or "0"
    return (Decimal(valor) / 100).quantize(Decimal("0.01"))


class CNAB750Service:
    # ------------------------------------------------------------------ #
    # Geração de arquivo padrão                                          #
    # ------------------------------------------------------------------ #
    @staticmethod
    def criar_arquivo_padrao(
        nome_arquivo: str,
        ispb_participante: str,
        tipo_pessoa_recebedor: str,
        cpf_cnpj: str,
        chave_pix: Optional[str] = None,
        nome_recebedor: Optional[str] = None,
        numero_sequencial_remessa: str = "1",
    ) -> str:
        """Cria um arquivo remessa CNAB750 padrão (apenas header e trailer)."""
        header = HeaderArquivo(
            ispb_participante=ispb_participante,
            tipo_pessoa_recebedor=tipo_pessoa_recebedor,
            cpf_cnpj=cpf_cnpj,
            chave_pix=chave_pix,
            nome_recebedor=nome_recebedor,
            data_geracao=datetime.now().date(),
            numero_sequencial_remessa=numero_sequencial_remessa,
        )
        arquivo = ArquivoRemessa(header=header, transacoes=[], trailer=TrailerArquivo())
        conteudo = CNAB750Service.json_to_cnab750(arquivo)

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        file_path = output_dir / f"{nome_arquivo}.rem"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(conteudo)
        return str(file_path)

    # ------------------------------------------------------------------ #
    # JSON -> CNAB750                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def json_to_cnab750(arquivo: ArquivoRemessa) -> str:
        """Converte um ``ArquivoRemessa`` em texto CNAB750 (registros de 750 bytes).

        O trailer (quantidade de registros e valor total) e os números
        sequenciais de registro são derivados automaticamente.
        """
        linhas = []
        seq = 1
        linhas.append(CNAB750Service._build_header(arquivo.header, seq))

        valor_total = Decimal("0")
        for detalhe in arquivo.transacoes:
            seq += 1
            linhas.append(CNAB750Service._build_detalhe(detalhe, seq))
            valor_total += Decimal(str(detalhe.valor_original or 0))

        seq += 1
        quantidade = len(arquivo.transacoes) + 2  # header + detalhes + trailer
        linhas.append(
            CNAB750Service._build_trailer(
                arquivo.trailer, seq, quantidade, valor_total
            )
        )
        return "\r\n".join(linhas)

    @staticmethod
    def _build_header(h: HeaderArquivo, seq_registro: int) -> str:
        linha = "".join(
            [
                _num(h.tipo_registro, 1),               # 001-001
                _num(h.operacao, 1),                    # 002-002
                _alpha(h.literal_remessa, 7),           # 003-009
                _num(h.codigo_servico, 2),              # 010-011
                _alpha(h.literal_servico, 15),          # 012-026
                _alpha(h.ispb_participante, 8),         # 027-034
                _num(h.tipo_pessoa_recebedor, 2),       # 035-036
                _num(h.cpf_cnpj, 14),                   # 037-050
                _num(h.agencia, 4),                     # 051-054
                _num(h.conta, 20),                      # 055-074
                _alpha(h.tipo_conta, 4),                # 075-078
                _alpha(h.chave_pix, 77),                # 079-155
                _data(h.data_geracao, 8),               # 156-163
                _alpha(h.codigo_convenio, 30),          # 164-193
                _alpha(h.exclusivo_psp, 60),            # 194-253
                _alpha(h.nome_recebedor, 100),          # 254-353
                _alpha("", 378),                        # 354-731 brancos
                _num(h.numero_sequencial_remessa, 10),  # 732-741
                _num(h.versao_arquivo, 3),              # 742-744
                _num(seq_registro, 6),                  # 745-750
            ]
        )
        return _assert_size(linha, "header")

    @staticmethod
    def _build_detalhe(d: RegistroDetalhe, seq_registro: int) -> str:
        linha = "".join(
            [
                _num(d.tipo_registro, 1),               # 001-001
                _alpha(d.identificador, 35),            # 002-036
                _num(d.tipo_pessoa_recebedor, 2),       # 037-038
                _num(d.cpf_cnpj, 14),                   # 039-052
                _num(d.agencia, 4),                     # 053-056
                _num(d.conta, 20),                      # 057-076
                _alpha(d.tipo_conta, 4),                # 077-080
                _alpha(d.chave_pix, 77),                # 081-157
                _alpha(d.tipo_cobranca, 1),             # 158-158
                _num(d.codigo_ocorrencia, 2),           # 159-160
                _num(d.timestamp_expiracao, 14),        # 161-174
                _data(d.data_vencimento, 8),            # 175-182
                _num(d.validade_apos_vencimento, 4),    # 183-186
                _valor(d.valor_original, 17),           # 187-203
                _num(d.tipo_pessoa_devedor, 2),         # 204-205
                _num(d.cpf_cnpj_devedor, 14),           # 206-219
                _alpha(d.nome_devedor, 140),            # 220-359
                _alpha(d.solicitacao_pagador, 140),     # 360-499
                _alpha(d.exclusivo_psp, 60),            # 500-559
                _alpha("", 185),                        # 560-744 brancos
                _num(seq_registro, 6),                  # 745-750
            ]
        )
        return _assert_size(linha, "detalhe")

    @staticmethod
    def _build_trailer(
        t: TrailerArquivo,
        seq_registro: int,
        quantidade: int,
        valor_total: Decimal,
    ) -> str:
        linha = "".join(
            [
                _num(t.tipo_registro, 1),   # 001-001
                _alpha("", 711),            # 002-712 brancos
                _valor(valor_total, 17),    # 713-729
                _num(quantidade, 15),       # 730-744
                _num(seq_registro, 6),      # 745-750
            ]
        )
        return _assert_size(linha, "trailer")

    # ------------------------------------------------------------------ #
    # CNAB750 -> JSON                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _quebrar_registros(conteudo: str) -> list:
        """Divide o conteúdo em registros de 750 bytes.

        Aceita arquivos com quebras de linha (``\\r\\n`` ou ``\\n``) ou sem
        nenhum delimitador (blocos fixos de 750 posições).
        """
        texto = conteudo.replace("\r\n", "\n").replace("\r", "\n")
        if "\n" in texto:
            registros = [l for l in texto.split("\n") if l.strip()]
        else:
            registros = [
                texto[i : i + RECORD_SIZE]
                for i in range(0, len(texto), RECORD_SIZE)
                if texto[i : i + RECORD_SIZE].strip()
            ]
        return registros

    @staticmethod
    def cnab750_to_json(conteudo: str) -> ArquivoRemessa:
        """Converte texto CNAB750 em um objeto ``ArquivoRemessa``."""
        registros = CNAB750Service._quebrar_registros(conteudo)
        if not registros:
            raise ValueError("Arquivo vazio")

        header = None
        transacoes = []
        trailer = None

        for linha in registros:
            if len(linha) < RECORD_SIZE:
                linha = linha.ljust(RECORD_SIZE)
            tipo = linha[0]
            if tipo == "0":
                header = CNAB750Service._parse_header(linha)
            elif tipo == "1":
                transacoes.append(CNAB750Service._parse_detalhe(linha))
            elif tipo == "9":
                trailer = CNAB750Service._parse_trailer(linha)

        if header is None or trailer is None:
            raise ValueError("Arquivo inválido: header ou trailer ausente")

        return ArquivoRemessa(header=header, transacoes=transacoes, trailer=trailer)

    @staticmethod
    def _parse_header(l: str) -> HeaderArquivo:
        return HeaderArquivo(
            tipo_registro=l[0:1],
            operacao=l[1:2],
            literal_remessa=_texto(l[2:9]) or "REMESSA",
            codigo_servico=l[9:11],
            literal_servico=_texto(l[11:26]) or "PIX",
            ispb_participante=_texto(l[26:34]) or "",
            tipo_pessoa_recebedor=l[34:36],
            cpf_cnpj=l[36:50].strip(),
            agencia=_texto(l[50:54]),
            conta=_texto(l[54:74]),
            tipo_conta=_texto(l[74:78]),
            chave_pix=_texto(l[78:155]),
            data_geracao=_parse_data(l[155:163]),
            codigo_convenio=_texto(l[163:193]),
            exclusivo_psp=_texto(l[193:253]),
            nome_recebedor=_texto(l[253:353]),
            numero_sequencial_remessa=l[731:741].strip() or "1",
            versao_arquivo=l[741:744],
            numero_sequencial_registro=l[744:750],
        )

    @staticmethod
    def _parse_detalhe(l: str) -> RegistroDetalhe:
        return RegistroDetalhe(
            tipo_registro=l[0:1],
            identificador=_texto(l[1:36]),
            tipo_pessoa_recebedor=l[36:38],
            cpf_cnpj=l[38:52].strip(),
            agencia=_texto(l[52:56]),
            conta=_texto(l[56:76]),
            tipo_conta=_texto(l[76:80]),
            chave_pix=_texto(l[80:157]) or "",
            tipo_cobranca=l[157:158],
            codigo_ocorrencia=l[158:160],
            timestamp_expiracao=_texto(l[160:174]),
            data_vencimento=_parse_data(l[174:182]),
            validade_apos_vencimento=_texto(l[182:186]),
            valor_original=_parse_valor(l[186:203]),
            tipo_pessoa_devedor=_texto(l[203:205]),
            cpf_cnpj_devedor=_texto(l[205:219]),
            nome_devedor=_texto(l[219:359]),
            solicitacao_pagador=_texto(l[359:499]),
            exclusivo_psp=_texto(l[499:559]),
            numero_sequencial=l[744:750],
        )

    @staticmethod
    def _parse_trailer(l: str) -> TrailerArquivo:
        return TrailerArquivo(
            tipo_registro=l[0:1],
            valor_total=_parse_valor(l[712:729]),
            quantidade_registros=int(l[729:744] or "0"),
            numero_sequencial=l[744:750],
        )
