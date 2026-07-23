"""Leitura de arquivos de RETORNO CNAB750, convertendo cada registro em JSON.

O arquivo de retorno só é recebido (não gerado pelo cliente), portanto este
serviço implementa apenas o sentido CNAB750 -> JSON. Cada registro de 750 bytes
é convertido para o schema correspondente ao seu tipo (0, 1, 2, 4, 5 e 9).
"""

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
    def retorno_to_json(conteudo: str) -> ArquivoRetorno:
        """Converte o texto de um arquivo de retorno em ``ArquivoRetorno``."""
        registros = RetornoService._quebrar_registros(conteudo)
        if not registros:
            raise ValueError("Arquivo vazio")

        header = None
        detalhes = []
        trailer = None

        for linha in registros:
            if len(linha) < RECORD_SIZE:
                linha = linha.ljust(RECORD_SIZE)
            tipo = linha[0]
            if tipo == "0":
                header = RetornoService._parse_header(linha)
            elif tipo == "1":
                detalhes.append(RetornoService._parse_transacao(linha))
            elif tipo == "2":
                detalhes.append(RetornoService._parse_info_adicional(linha))
            elif tipo == "4":
                detalhes.append(RetornoService._parse_emv(linha))
            elif tipo == "5":
                detalhes.append(RetornoService._parse_recebimento(linha))
            elif tipo == "9":
                trailer = RetornoService._parse_trailer(linha)
            else:
                raise ValueError(f"Tipo de registro desconhecido: '{tipo}'")

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
