"""Leitura de arquivos de RETORNO CNAB750, convertendo cada registro em JSON.

O arquivo de retorno só é recebido (não gerado pelo cliente), portanto este
serviço implementa apenas o sentido CNAB750 -> JSON. Cada registro de 750 bytes
é convertido para o schema correspondente ao seu tipo (0, 1, 2, 4, 5 e 9).
"""

from typing import BinaryIO, Iterator, Tuple

from ..schemas.retorno import (
    ArquivoRetorno,
    HeaderRetorno,
    RetornoEmv,
    RetornoInfoAdicional,
    RetornoRecebimento,
    RetornoTransacao,
    TrailerRetorno,
)
from .cnab750_service import RECORD_SIZE, _parse_data, _parse_valor, _texto

# Tamanho de leitura ao processar arquivos em streaming (1 MiB).
CHUNK_SIZE = 1 << 20


class _SplitterRegistros:
    """Divide um fluxo de *bytes* em registros de 750 posições, incrementalmente.

    Detecta o modo do arquivo a partir dos primeiros bytes — delimitado por
    quebra de linha (``\\r\\n``/``\\r``/``\\n``) ou blocos fixos de 750 — e
    mantém estado entre chamadas de :meth:`feed`, de modo que o arquivo nunca
    precisa ser carregado inteiro na memória.
    """

    def __init__(self, encoding: str = "utf-8"):
        self._buf = bytearray()
        self._modo = None  # "linha" | "fixo"
        self._encoding = encoding

    def _detectar_modo(self) -> None:
        head = bytes(self._buf[: RECORD_SIZE + 2])
        self._modo = "linha" if (b"\n" in head or b"\r" in head) else "fixo"

    def feed(self, dados: bytes) -> Iterator[str]:
        """Adiciona bytes ao buffer e emite os registros já completos."""
        self._buf.extend(dados)
        if self._modo is None:
            # Só decide o modo com bytes suficientes para ver o delimitador que
            # segue o 1º registro (posições 750/751); antes disso é ambíguo.
            if len(self._buf) < RECORD_SIZE + 2:
                return
            self._detectar_modo()
        yield from self._emitir(final=False)

    def flush(self) -> Iterator[str]:
        """Emite o que restou no buffer ao final do fluxo."""
        if self._modo is None and self._buf.strip():
            self._detectar_modo()
        yield from self._emitir(final=True)

    def _emitir(self, final: bool) -> Iterator[str]:
        # Percorre o buffer com um cursor e remove o prefixo consumido uma
        # única vez ao final. Apagar do início a cada registro (``del buf[:k]``)
        # seria O(n²), pois desloca o restante do buffer a cada chamada.
        buf = self._buf
        pos = 0
        n = len(buf)
        if self._modo == "linha":
            while True:
                i_n = buf.find(b"\n", pos)
                i_r = buf.find(b"\r", pos)
                if i_n == -1 and i_r == -1:
                    break
                if i_n == -1:
                    idx = i_r
                elif i_r == -1:
                    idx = i_n
                else:
                    idx = i_n if i_n < i_r else i_r
                linha = bytes(buf[pos:idx])
                pos = idx + 1
                if linha.strip():
                    yield linha.decode(self._encoding)
        elif self._modo == "fixo":
            while n - pos >= RECORD_SIZE:
                bloco = bytes(buf[pos : pos + RECORD_SIZE])
                pos += RECORD_SIZE
                if bloco.strip():
                    yield bloco.decode(self._encoding)

        if pos:
            del buf[:pos]

        if final and buf.strip():
            yield bytes(buf).decode(self._encoding)
            buf.clear()


class RetornoService:
    @staticmethod
    def _quebrar_registros(conteudo: str) -> list:
        """Divide o conteúdo em registros de 750 bytes.

        Aceita quebras de linha (``\\r\\n``/``\\n``) ou blocos fixos de 750.
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
    def parse_linha(linha: str) -> Tuple[str, object]:
        """Converte uma linha de 750 posições no objeto do seu tipo.

        Retorna ``(secao, objeto)`` em que ``secao`` é ``"header"``,
        ``"detalhe"`` ou ``"trailer"``.
        """
        if len(linha) < RECORD_SIZE:
            linha = linha.ljust(RECORD_SIZE)
        tipo = linha[0]
        if tipo == "0":
            return "header", RetornoService._parse_header(linha)
        if tipo == "1":
            return "detalhe", RetornoService._parse_transacao(linha)
        if tipo == "2":
            return "detalhe", RetornoService._parse_info_adicional(linha)
        if tipo == "4":
            return "detalhe", RetornoService._parse_emv(linha)
        if tipo == "5":
            return "detalhe", RetornoService._parse_recebimento(linha)
        if tipo == "9":
            return "trailer", RetornoService._parse_trailer(linha)
        raise ValueError(f"Tipo de registro desconhecido: '{tipo}'")

    @staticmethod
    def iter_registros(fp: BinaryIO, chunk_size: int = CHUNK_SIZE) -> Iterator[str]:
        """Itera as linhas de 750 posições de um arquivo binário, em streaming.

        Lê ``fp`` em blocos de ``chunk_size`` bytes, sem materializar o arquivo
        inteiro. Aceita também objetos que devolvam ``str`` em ``read``.
        """
        splitter = _SplitterRegistros()
        while True:
            pedaco = fp.read(chunk_size)
            if not pedaco:
                break
            if isinstance(pedaco, str):
                pedaco = pedaco.encode("utf-8")
            yield from splitter.feed(pedaco)
        yield from splitter.flush()

    @staticmethod
    def retorno_to_json(conteudo: str) -> ArquivoRetorno:
        """Converte o texto de um arquivo de retorno em ``ArquivoRetorno``."""
        registros = RetornoService._quebrar_registros(conteudo)
        if not registros:
            raise ValueError("Arquivo vazio")
        return RetornoService._montar_arquivo(iter(registros))

    @staticmethod
    def retorno_to_json_stream(fp: BinaryIO) -> ArquivoRetorno:
        """Versão em streaming de :meth:`retorno_to_json`.

        Consome ``fp`` (arquivo binário) incrementalmente, sem carregar o
        conteúdo inteiro na memória. O uso de memória do *parsing* fica
        limitado a um registro por vez; a lista de detalhes ainda cresce com a
        quantidade de registros (a resposta JSON é integral).
        """
        return RetornoService._montar_arquivo(RetornoService.iter_registros(fp))

    @staticmethod
    def resumo_stream(fp: BinaryIO) -> "ResumoRetorno":
        """Calcula os indicadores de receita em um único passe, em streaming.

        Ao contrário de :meth:`retorno_to_json_stream`, a saída é **limitada**:
        só os totais e as agregações por dia e por chave Pix ficam em memória,
        de forma que arquivos de qualquer tamanho são processados com memória
        constante. É a primitiva escalável para a análise de receita.
        """
        from decimal import Decimal

        from ..schemas.retorno import ResumoGrupo, ResumoRetorno

        ZERO = Decimal("0")

        def _v(x):
            return x if x is not None else ZERO

        resumo = ResumoRetorno()
        por_dia = {}
        por_chave = {}

        def _acumula(mapa, chave, pago, tarifa):
            if not chave:
                return
            g = mapa.get(chave)
            if g is None:
                mapa[chave] = [1, pago, tarifa]
            else:
                g[0] += 1
                g[1] += pago
                g[2] += tarifa

        # Caminho rápido: para os recebimentos (tipo 5) extraímos direto os
        # poucos campos necessários, sem construir o modelo Pydantic completo
        # (~2,5x mais rápido). Os offsets espelham ``_parse_recebimento``.
        for linha in RetornoService.iter_registros(fp):
            if len(linha) < RECORD_SIZE:
                linha = linha.ljust(RECORD_SIZE)
            tipo = linha[0]

            if tipo == "5":
                pago = _v(_parse_valor(linha[300:317]))
                tarifa = _v(_parse_valor(linha[727:744]))
                resumo.quantidade += 1
                resumo.valor_original += _v(_parse_valor(linha[198:215]))
                resumo.valor_juros += _v(_parse_valor(linha[215:232]))
                resumo.valor_multa += _v(_parse_valor(linha[232:249]))
                resumo.valor_abatimento += _v(_parse_valor(linha[249:266]))
                resumo.valor_desconto += _v(_parse_valor(linha[266:283]))
                resumo.receita_bruta += pago
                resumo.tarifas += tarifa

                data = _parse_data(linha[168:176])
                if data is not None:
                    _acumula(por_dia, data.isoformat(), pago, tarifa)
                _acumula(por_chave, _texto(linha[88:165]), pago, tarifa)

            elif tipo == "0":
                h = RetornoService._parse_header(linha)
                resumo.ispb_participante = h.ispb_participante
                resumo.nome_recebedor = h.nome_recebedor
                resumo.data_geracao = h.data_geracao
            # Demais tipos (1, 2, 4 e 9) não entram no resumo de receita.

        resumo.receita_liquida = resumo.receita_bruta - resumo.tarifas
        if resumo.quantidade:
            resumo.ticket_medio = resumo.receita_bruta / resumo.quantidade

        def _grupos(mapa):
            return [
                ResumoGrupo(
                    chave=k,
                    quantidade=v[0],
                    valor_pago=v[1],
                    tarifa=v[2],
                    receita_liquida=v[1] - v[2],
                )
                for k, v in sorted(mapa.items())
            ]

        resumo.por_dia = _grupos(por_dia)
        resumo.por_chave = _grupos(por_chave)
        return resumo

    @staticmethod
    def _montar_arquivo(linhas: Iterator[str]) -> ArquivoRetorno:
        header = None
        detalhes = []
        trailer = None
        vazio = True

        for linha in linhas:
            vazio = False
            secao, obj = RetornoService.parse_linha(linha)
            if secao == "header":
                header = obj
            elif secao == "trailer":
                trailer = obj
            else:
                detalhes.append(obj)

        if vazio:
            raise ValueError("Arquivo vazio")
        if header is None or trailer is None:
            raise ValueError("Arquivo de retorno inválido: header ou trailer ausente")

        return ArquivoRetorno(header=header, detalhes=detalhes, trailer=trailer)

    # ------------------------------------------------------------------ #
    # Parsers por tipo de registro                                        #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_header(l: str) -> HeaderRetorno:
        return HeaderRetorno(
            tipo_registro=l[0:1],
            codigo_retorno=l[1:2],
            literal_retorno=_texto(l[2:9]) or "RETORNO",
            codigo_servico=l[9:11],
            literal_servico=_texto(l[11:26]) or "PIX",
            ispb_participante=_texto(l[26:34]),
            tipo_pessoa_recebedor=_texto(l[34:36]),
            cpf_cnpj=_texto(l[36:50]),
            agencia=_texto(l[50:54]),
            conta=_texto(l[54:74]),
            tipo_conta=_texto(l[74:78]),
            chave_pix=_texto(l[78:155]),
            data_geracao=_parse_data(l[155:163]),
            codigo_convenio=_texto(l[163:193]),
            exclusivo_psp=_texto(l[193:253]),
            nome_recebedor=_texto(l[253:353]),
            codigos_erro=_texto(l[353:383]),
            numero_sequencial_retorno=_texto(l[731:741]),
            versao_arquivo=_texto(l[741:744]),
            numero_sequencial_registro=_texto(l[744:750]),
        )

    @staticmethod
    def _parse_transacao(l: str) -> RetornoTransacao:
        return RetornoTransacao(
            tipo_registro=l[0:1],
            identificador=_texto(l[1:36]),
            tipo_pessoa_recebedor=_texto(l[36:38]),
            cpf_cnpj=_texto(l[38:52]),
            agencia=_texto(l[52:56]),
            conta=_texto(l[56:76]),
            tipo_conta=_texto(l[76:80]),
            chave_pix=_texto(l[80:157]),
            tipo_cobranca=_texto(l[157:158]),
            codigo_movimento=_texto(l[158:160]),
            timestamp_expiracao=_texto(l[160:174]),
            data_vencimento=_parse_data(l[174:182]),
            validade_apos_vencimento=_texto(l[182:186]),
            valor_original=_parse_valor(l[186:203]),
            tipo_pessoa_devedor=_texto(l[203:205]),
            cpf_cnpj_devedor=_texto(l[205:219]),
            nome_devedor=_texto(l[219:359]),
            solicitacao_pagador=_texto(l[359:499]),
            exclusivo_psp=_texto(l[499:559]),
            data_movimento=_parse_data(l[559:567]),
            codigos_erro=_texto(l[567:597]),
            revisao=_texto(l[597:601]),
            tarifa_cobranca=_parse_valor(l[601:618]),
            numero_sequencial=_texto(l[744:750]),
        )

    @staticmethod
    def _parse_info_adicional(l: str) -> RetornoInfoAdicional:
        return RetornoInfoAdicional(
            tipo_registro=l[0:1],
            identificador=_texto(l[1:36]),
            nome_1=_texto(l[36:86]),
            valor_1=_texto(l[86:286]),
            nome_2=_texto(l[286:336]),
            valor_2=_texto(l[336:536]),
            numero_sequencial=_texto(l[744:750]),
        )

    @staticmethod
    def _parse_emv(l: str) -> RetornoEmv:
        return RetornoEmv(
            tipo_registro=l[0:1],
            identificador=_texto(l[1:36]),
            chave_pix=_texto(l[36:113]),
            codigo_movimento=_texto(l[113:115]),
            data_movimento=_parse_data(l[115:123]),
            emv_qrcode=_texto(l[123:623]),
            location=_texto(l[623:700]),
            numero_sequencial=_texto(l[744:750]),
        )

    @staticmethod
    def _parse_recebimento(l: str) -> RetornoRecebimento:
        return RetornoRecebimento(
            tipo_registro=l[0:1],
            identificador=_texto(l[1:36]),
            ispb_participante=_texto(l[36:44]),
            tipo_pessoa=_texto(l[44:46]),
            cpf_cnpj=_texto(l[46:60]),
            agencia=_texto(l[60:64]),
            conta=_texto(l[64:84]),
            tipo_conta=_texto(l[84:88]),
            chave_pix=_texto(l[88:165]),
            tipo_cobranca=_texto(l[165:166]),
            codigo_movimento=_texto(l[166:168]),
            data_movimento=_parse_data(l[168:176]),
            data_vencimento=_parse_data(l[176:184]),
            timestamp_pagamento=_texto(l[184:198]),
            valor_original=_parse_valor(l[198:215]),
            valor_juros=_parse_valor(l[215:232]),
            valor_multa=_parse_valor(l[232:249]),
            valor_abatimento=_parse_valor(l[249:266]),
            valor_desconto=_parse_valor(l[266:283]),
            valor_final=_parse_valor(l[283:300]),
            valor_pago=_parse_valor(l[300:317]),
            tipo_pessoa_devedor=_texto(l[317:319]),
            cpf_cnpj_devedor=_texto(l[319:333]),
            tipo_pessoa_pagador_final=_texto(l[333:335]),
            cpf_cnpj_pagador_final=_texto(l[335:349]),
            nome_pagador_final=_texto(l[349:489]),
            mensagem_pagador_final=_texto(l[489:629]),
            codigo_liquidacao=_texto(l[629:631]),
            end_to_end_id=_texto(l[631:663]),
            revisao=_texto(l[663:667]),
            exclusivo_psp=_texto(l[667:727]),
            tarifa_cobranca=_parse_valor(l[727:744]),
            numero_sequencial=_texto(l[744:750]),
        )

    @staticmethod
    def _parse_trailer(l: str) -> TrailerRetorno:
        return TrailerRetorno(
            tipo_registro=l[0:1],
            codigo_retorno=l[1:2],
            codigo_servico=l[2:4],
            ispb=_texto(l[4:12]),
            codigos_erro=_texto(l[12:42]),
            valor_total=_parse_valor(l[712:729]),
            quantidade_detalhes=int(l[729:744] or "0"),
            numero_sequencial=_texto(l[744:750]),
        )
