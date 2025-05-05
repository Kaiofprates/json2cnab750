# JSON2CNAB750

API para criação de arquivos CNAB750 padrão, com suporte ao PIX automático.

## Funcionalidades

- Criação de arquivo CNAB750 padrão sem transações

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

#### POST /api/v1/criar-arquivo-padrao

Cria um arquivo CNAB750 padrão sem transações. O arquivo será salvo na pasta `output` do projeto.

Exemplo de requisição:
```json
{
    "nome_arquivo": "meu_arquivo",
    "codigo_empresa": "1234567890",
    "nome_empresa": "MINHA EMPRESA LTDA",
    "numero_banco": "341",
    "nome_banco": "BANCO ITAU"
}
```

Observações:
- Os campos serão automaticamente preenchidos com espaços à direita para atingir o tamanho correto
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