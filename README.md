# JSON2CNAB750

API para conversão entre JSON e arquivos CNAB750 (padrão Pix Automático / Itaú),
nos dois sentidos. Os registros seguem o documento oficial
`Layout_padrao_CNAB750_V2_1` (Header `0`, Detalhe `1` e Trailer `9`), cada um
com exatamente **750 bytes**.

## Funcionalidades

- **Site web** para enviar o arquivo de retorno e ver a análise no navegador,
  com filtros e download da planilha (servido pela própria API em `/`)
- Conversão de JSON para CNAB750 remessa (`/json-to-cnab750`)
- Conversão de CNAB750 remessa para JSON (`/cnab750-to-json`)
- Leitura de arquivo de RETORNO CNAB750, com cada registro convertido em JSON (`/retorno-to-json`)
- Análise de RETORNO em Excel (.xlsx) com sumarização de receita (`/retorno-to-excel`)
- Criação de arquivo CNAB750 padrão sem transações (`/criar-arquivo-padrao`)
- Geração automática do trailer (quantidade de registros e valor total) e dos
  números sequenciais de registro

## Requisitos

- Python 3.8+
- Dependências listadas em `requirements.txt`

## Instalação

1. Clone o repositório
2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```
3. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Uso

Para iniciar o servidor de desenvolvimento:

```bash
uvicorn app.main:app --reload
```

- Site web: `http://localhost:8000/`
- Documentação da API (Swagger): `http://localhost:8000/docs`

### Interface Web

O endereço raiz (`/`) serve uma aplicação de página única (HTML/CSS/JS, sem
build) que consome os próprios endpoints da API. O fluxo é:

1. Envie um arquivo de **retorno** CNAB750 (arraste ou selecione).
2. A página chama `/retorno-to-json` e renderiza no navegador:
   - **Resumo da receita** — os mesmos indicadores da planilha (valor original,
     juros, multa, descontos, abatimentos, receita bruta, tarifas, receita
     líquida, ticket médio), recalculados conforme os filtros aplicados;
   - **Receita por dia** (com mini-gráfico de barras) e **por chave Pix**;
   - **Tabela de recebimentos** com filtros por data, valor e busca textual
     (chave/pagador/TxID) e ordenação por coluna.
3. O botão **Baixar Excel** reenvia o arquivo para `/retorno-to-excel` e baixa a
   planilha `.xlsx`.

Os arquivos do frontend ficam em [`frontend/`](frontend/) e são servidos pela
FastAPI via `StaticFiles`.

### Endpoints

#### POST /api/v1/json-to-cnab750

Converte um JSON no formato `ArquivoRemessa` para texto CNAB750. Veja um payload
completo em [`examples/exemplo_remessa.json`](examples/exemplo_remessa.json).
O trailer e os números sequenciais de registro são derivados automaticamente, ou
seja, não precisam ser enviados.

#### POST /api/v1/cnab750-to-json

Recebe um arquivo CNAB750 (`multipart/form-data`, campo `arquivo`) e devolve o
JSON correspondente. Aceita registros separados por quebra de linha
(`\r\n`/`\n`) ou concatenados em blocos fixos de 750 posições.

#### POST /api/v1/retorno-to-json

Recebe um arquivo de **retorno** CNAB750 (`multipart/form-data`, campo
`arquivo`) e devolve o JSON com cada registro convertido. O arquivo de retorno
é heterogêneo e a rota reconhece todos os tipos de registro do leiaute:

| Tipo | Registro |
|------|----------|
| `0`  | Header |
| `1`  | Retorno de emissão, alteração e cancelamento |
| `2`  | Informações adicionais (recebimento) |
| `4`  | Geração do QR Code / EMV (emissão) |
| `5`  | Recebimento |
| `9`  | Trailer |

A resposta tem a forma `{ "header": {...}, "detalhes": [...], "trailer": {...} }`,
em que cada item de `detalhes` traz o campo `tipo_registro` identificando o seu
tipo. Aceita registros separados por quebra de linha ou em blocos fixos de 750.

#### POST /api/v1/retorno-to-excel

Recebe um arquivo de **retorno** CNAB750 (`multipart/form-data`, campo
`arquivo`) e devolve uma planilha **Excel (`.xlsx`)** com a análise dos
recebimentos (registros tipo `5`) e sumarização de receita. A planilha tem
quatro abas:

| Aba | Conteúdo |
|-----|----------|
| `Resumo` | Indicadores consolidados: qtde. de recebimentos, valor original, juros, multa, descontos, abatimentos, **receita bruta** (valor pago), tarifas, **receita líquida** e ticket médio |
| `Recebimentos` | Uma linha por recebimento (detalhe) |
| `Receita por Dia` | Sumarização por data de movimento |
| `Receita por Chave` | Sumarização por chave Pix do recebedor |

Todos os totais são gravados como **fórmulas** (`SUM`, `SUMIFS`, `COUNTIFS`),
de modo que a planilha recalcula automaticamente ao ser editada.

#### POST /api/v1/criar-arquivo-padrao

Cria um arquivo CNAB750 padrão sem transações (apenas header e trailer). O
arquivo será salvo na pasta `output` do projeto.

Exemplo de requisição:
```json
{
    "nome_arquivo": "meu_arquivo",
    "ispb_participante": "60701190",
    "tipo_pessoa_recebedor": "02",
    "cpf_cnpj": "12345678901234",
    "chave_pix": "recebedor@email.com",
    "nome_recebedor": "MINHA EMPRESA LTDA",
    "numero_sequencial_remessa": "1"
}
```

Observações:
- Campos alfanuméricos são completados com espaços à direita e numéricos com
  zeros à esquerda para atingir o tamanho exato de cada posição
- O arquivo será salvo em `output/nome_arquivo.rem`
- A resposta incluirá o caminho completo do arquivo gerado

## Deploy em produção

O projeto inclui scripts para publicar a API + site num **VPS Hostinger**
(Ubuntu/Debian) com Gunicorn + Nginx + systemd. Em resumo, no VPS:

```bash
git clone https://github.com/kaiofprates/json2cnab750.git
cd json2cnab750/deploy
SERVER_NAME=meudominio.com.br ./deploy.sh
```

O script é idempotente (serve tanto para o primeiro deploy quanto para
atualizações) e pode emitir HTTPS via Let's Encrypt. Detalhes, variáveis e
operação em [`deploy/README.md`](deploy/README.md).

## Estrutura do Projeto

```
.
├── app/
│   ├── api/            # Rotas da API
│   ├── core/           # Configurações centrais
│   ├── models/         # Modelos de dados
│   ├── schemas/        # Schemas Pydantic
│   └── services/       # Lógica de negócios
├── frontend/          # Site web (SPA estática servida pela API)
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── deploy/            # Scripts e configs de deploy (VPS Hostinger)
│   ├── deploy.sh
│   ├── json2cnab750.service
│   ├── nginx.conf
│   └── README.md
├── output/            # Pasta onde os arquivos são salvos
├── requirements.txt   # Dependências
├── requirements-prod.txt  # Dependências extras de produção (gunicorn)
└── README.md         # Este arquivo
``` 