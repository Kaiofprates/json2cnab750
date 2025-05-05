from datetime import datetime
import os
from pathlib import Path

from ..schemas.cnab750 import ArquivoRemessa, HeaderArquivo, RegistroTransacao, TrailerArquivo

class CNAB750Service:
    @staticmethod
    def criar_arquivo_padrao(
        nome_arquivo: str,
        codigo_empresa: str,
        nome_empresa: str,
        numero_banco: str,
        nome_banco: str
    ) -> str:
        """Cria um arquivo CNAB750 padrão sem transações."""
        data_atual = datetime.now()
        
        # Cria o header padrão
        header = HeaderArquivo(
            codigo_registro="0",
            codigo_remessa="1",
            literal_remessa="REMESSA",
            codigo_servico="20",
            literal_servico="PIX AUTOMATICO ".ljust(15),
            codigo_empresa=codigo_empresa,
            nome_empresa=nome_empresa,
            numero_banco=numero_banco,
            nome_banco=nome_banco,
            data_geracao=data_atual.date(),
            densidade_gravacao="01600",
            literal_densidade="BPI",
            numero_sequencial="1"
        )
        
        # Cria o trailer padrão
        trailer = TrailerArquivo(
            codigo_registro="9",
            quantidade_registros=0,
            valor_total=0.0,
            numero_sequencial="2"
        )
        
        # Cria o arquivo remessa
        arquivo = ArquivoRemessa(
            header=header,
            transacoes=[],
            trailer=trailer
        )
        
        # Converte para CNAB750
        conteudo = CNAB750Service.json_to_cnab750(arquivo)
        
        # Cria o diretório de saída se não existir
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Salva o arquivo
        file_path = output_dir / f"{nome_arquivo}.rem"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(conteudo)
        
        return str(file_path)
    
    @staticmethod
    def json_to_cnab750(arquivo: ArquivoRemessa) -> str:
        """Converte um objeto ArquivoRemessa para uma string no formato CNAB750."""
        linhas = []
        
        # Header
        header = CNAB750Service._formatar_header(arquivo.header)
        linhas.append(header)
        
        # Transações
        for transacao in arquivo.transacoes:
            linha = CNAB750Service._formatar_transacao(transacao)
            linhas.append(linha)
        
        # Trailer
        trailer = CNAB750Service._formatar_trailer(arquivo.trailer)
        linhas.append(trailer)
        
        return "\r\n".join(linhas)
    
    @staticmethod
    def _formatar_header(header: HeaderArquivo) -> str:
        """Formata o registro header conforme layout CNAB750."""
        return (
            f"{header.codigo_registro:<1}"
            f"{header.codigo_remessa:<1}"
            f"{header.literal_remessa:<7}"
            f"{header.codigo_servico:<2}"
            f"{header.literal_servico:<15}"
            f"{header.codigo_empresa:<20}"
            f"{header.nome_empresa:<30}"
            f"{header.numero_banco:<3}"
            f"{header.nome_banco:<15}"
            f"{header.data_geracao.strftime('%d%m%y'):<6}"
            f"{header.densidade_gravacao:<5}"
            f"{header.literal_densidade:<3}"
            f"{' ' * 528}"  # Complemento do registro (750 - 222 caracteres já usados)
            f"{header.numero_sequencial:>7}"
        )
    
    @staticmethod
    def _formatar_transacao(transacao: RegistroTransacao) -> str:
        """Formata o registro de transação conforme layout CNAB750."""
        linha = (
            f"{transacao.codigo_registro:<1}"
            f"{transacao.tipo_inscricao:<2}"
            f"{transacao.numero_inscricao:<14}"
            f"{transacao.identificacao_empresa:<14}"
            f"{transacao.nosso_numero:<8}"
            f"{transacao.data_vencimento.strftime('%d%m%y'):<6}"
            f"{int(transacao.valor_titulo * 100):013d}"
            f"{transacao.especie_titulo:<2}"
            f"{transacao.identificacao_titulo:<10}"
            f"{transacao.nome_pagador:<30}"
            f"{transacao.endereco_pagador:<40}"
        )
        
        # Adiciona código de barras ou chave PIX se disponível
        if transacao.codigo_barras:
            linha += f"{transacao.codigo_barras:<44}"
        elif transacao.chave_pix:
            linha += f"{transacao.chave_pix:<44}"
        else:
            linha += " " * 44
            
        # Complemento do registro
        linha += " " * 559
        
        # Número sequencial do registro
        linha += f"{transacao.nosso_numero:>7}"
        
        return linha
    
    @staticmethod
    def _formatar_trailer(trailer: TrailerArquivo) -> str:
        """Formata o registro trailer conforme layout CNAB750."""
        return (
            f"{trailer.codigo_registro:<1}"
            f"{trailer.quantidade_registros:06d}"
            f"{int(trailer.valor_total * 100):013d}"
            f"{' ' * 723}"  # Complemento do registro
            f"{trailer.numero_sequencial:>7}"
        )
    
    @staticmethod
    def cnab750_to_json(conteudo: str) -> ArquivoRemessa:
        """Converte uma string no formato CNAB750 para um objeto ArquivoRemessa."""
        linhas = conteudo.split("\r\n")
        
        if not linhas:
            raise ValueError("Arquivo vazio")
            
        header = None
        transacoes = []
        trailer = None
        
        for linha in linhas:
            if not linha:
                continue
                
            tipo_registro = linha[0]
            
            if tipo_registro == "0":
                header = CNAB750Service._parse_header(linha)
            elif tipo_registro == "1":
                transacao = CNAB750Service._parse_transacao(linha)
                transacoes.append(transacao)
            elif tipo_registro == "9":
                trailer = CNAB750Service._parse_trailer(linha)
                
        if not all([header, trailer]):
            raise ValueError("Arquivo inválido: header ou trailer ausente")
            
        return ArquivoRemessa(
            header=header,
            transacoes=transacoes,
            trailer=trailer
        )
    
    @staticmethod
    def _parse_header(linha: str) -> HeaderArquivo:
        """Converte uma linha de header CNAB750 para objeto HeaderArquivo."""
        return HeaderArquivo(
            codigo_registro=linha[0:1],
            codigo_remessa=linha[1:2],
            literal_remessa=linha[2:9].strip(),
            codigo_servico=linha[9:11],
            literal_servico=linha[11:26].strip(),
            codigo_empresa=linha[26:46].strip(),
            nome_empresa=linha[46:76].strip(),
            numero_banco=linha[76:79],
            nome_banco=linha[79:94].strip(),
            data_geracao=datetime.strptime(linha[94:100], "%d%m%y").date(),
            densidade_gravacao=linha[100:105],
            literal_densidade=linha[105:108],
            numero_sequencial=linha[743:750]
        )
    
    @staticmethod
    def _parse_transacao(linha: str) -> RegistroTransacao:
        """Converte uma linha de transação CNAB750 para objeto RegistroTransacao."""
        valor_titulo = int(linha[45:58]) / 100
        
        # Verifica se há código de barras ou chave PIX
        codigo_barras_ou_pix = linha[146:190].strip()
        codigo_barras = None
        chave_pix = None
        
        if codigo_barras_ou_pix:
            if codigo_barras_ou_pix.isdigit():
                codigo_barras = codigo_barras_ou_pix
            else:
                chave_pix = codigo_barras_ou_pix
        
        return RegistroTransacao(
            codigo_registro=linha[0:1],
            tipo_inscricao=linha[1:3],
            numero_inscricao=linha[3:17],
            identificacao_empresa=linha[17:31].strip(),
            nosso_numero=linha[31:39],
            data_vencimento=datetime.strptime(linha[39:45], "%d%m%y").date(),
            valor_titulo=valor_titulo,
            especie_titulo=linha[58:60],
            identificacao_titulo=linha[60:70].strip(),
            nome_pagador=linha[70:100].strip(),
            endereco_pagador=linha[100:140].strip(),
            codigo_barras=codigo_barras,
            chave_pix=chave_pix
        )
    
    @staticmethod
    def _parse_trailer(linha: str) -> TrailerArquivo:
        """Converte uma linha de trailer CNAB750 para objeto TrailerArquivo."""
        return TrailerArquivo(
            codigo_registro=linha[0:1],
            quantidade_registros=int(linha[1:7]),
            valor_total=int(linha[7:20]) / 100,
            numero_sequencial=linha[743:750]
        ) 