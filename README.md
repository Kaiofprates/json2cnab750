# JSON2CNAB750

API para conversão entre JSON e arquivos CNAB750 (padrão Pix Automático / Itaú),
nos dois sentidos. Os registros seguem o documento oficial
`Layout_padrao_CNAB750_V2_1` (Header `0`, Detalhe `1` e Trailer `9`), cada um
com exatamente **750 bytes**.

## Funcionalidades

- Conversão de JSON para CNAB750 (`/json-to-cnab750`)
- Conversão de CNAB750 para JSON (`/cnab750-to-json`)
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

A documentação da API estará disponível em `http://localhost:8000/docs`

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

## Estrutura do Projeto

```
.
├── app/
│   ├── api/            # Rotas da API
│   ├── core/           # Configurações centrais
│   ├── models/         # Modelos de dados
│   ├── schemas/        # Schemas Pydantic
│   └── services/       # Lógica de negócios
├── output/            # Pasta onde os arquivos são salvos
├── requirements.txt   # Dependências
└── README.md         # Este arquivo
``` 