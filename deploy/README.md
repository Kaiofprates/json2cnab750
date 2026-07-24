# Deploy em VPS Hostinger

Guia para colocar a API **e o site** JSON2CNAB750 em produção num VPS da
Hostinger (Ubuntu 22.04/24.04 ou Debian 12). O frontend é servido pela própria
FastAPI, então o deploy é um único serviço: **Gunicorn (Uvicorn workers)** atrás
do **Nginx**, gerenciado pelo **systemd**.

```
Navegador ──HTTPS──> Nginx (80/443) ──proxy──> Gunicorn 127.0.0.1:8000 ──> FastAPI
                                                        │
                                                        └── serve o frontend (/ e /static)
```

## Arquivos

| Arquivo | Função |
|---------|--------|
| `deploy.sh` | Script idempotente de provisionamento/atualização |
| `json2cnab750.service` | Template da unidade systemd |
| `nginx.conf` | Template do site Nginx (proxy reverso) |

## Pré-requisitos

1. Um VPS Hostinger com Ubuntu/Debian e acesso `root` via SSH
   (painel hPanel → VPS → *Sistema operacional*).
2. (Opcional, para HTTPS) um domínio com registro **A** apontando para o IP do VPS.

## Passo a passo

### 1. Acesse o VPS

```bash
ssh root@SEU_IP_DA_HOSTINGER
```

### 2. Rode o deploy

O script instala tudo sozinho. Basta baixá-lo (ou clonar o repositório) e executar:

```bash
# opção A: clonar e rodar
git clone https://github.com/kaiofprates/json2cnab750.git
cd json2cnab750/deploy
SERVER_NAME=meudominio.com.br ./deploy.sh

# opção B: sem domínio ainda (acessa pelo IP)
./deploy.sh
```

Na primeira execução ele:
- instala Python, Nginx e Git;
- cria o usuário de sistema `json2cnab`;
- clona o projeto em `/opt/json2cnab750`;
- cria o virtualenv e instala as dependências;
- registra e inicia o serviço systemd;
- configura o Nginx como proxy reverso.

Ao terminar, o site já responde em `http://SEU_IP/`.

### 3. Habilite HTTPS (recomendado)

Com o DNS do domínio apontando para o VPS:

```bash
cd /opt/json2cnab750/deploy   # ou onde clonou
RUN_CERTBOT=1 SERVER_NAME=meudominio.com.br ./deploy.sh
```

Ou manualmente:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d meudominio.com.br
```

## Atualizações (novo deploy)

Para publicar mudanças já mergeadas na branch, rode de novo — é rápido porque
pula os pacotes de sistema:

```bash
cd /opt/json2cnab750/deploy
SKIP_APT=1 SERVER_NAME=meudominio.com.br ./deploy.sh
```

O script faz `git fetch/checkout` da branch, reinstala dependências se mudaram e
reinicia o serviço.

## Operação

```bash
# status e logs
systemctl status json2cnab750
journalctl -u json2cnab750 -f

# reiniciar / parar
systemctl restart json2cnab750
systemctl stop json2cnab750

# testar config do nginx e recarregar
nginx -t && systemctl reload nginx
```

## Variáveis do deploy.sh

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SERVER_NAME` | `_` | Domínio do site (`_` = responde em qualquer host/IP) |
| `REPO_URL` | repo do projeto | URL do git a implantar |
| `BRANCH` | `main` | Branch a publicar |
| `APP_USER` | `json2cnab` | Usuário de sistema da aplicação |
| `APP_DIR` | `/opt/json2cnab750` | Diretório de instalação |
| `PYTHON` | `python3` | Interpretador base |
| `SKIP_APT` | `0` | `1` pula instalação de pacotes (updates rápidos) |
| `RUN_CERTBOT` | `0` | `1` emite certificado HTTPS ao final |

## Ajustes finos

- **Nº de workers Gunicorn:** edite `--workers` em
  `/etc/systemd/system/json2cnab750.service` (regra prática: `2 × núcleos + 1`)
  e rode `systemctl daemon-reload && systemctl restart json2cnab750`.
- **Tamanho máximo de upload:** `client_max_body_size` em `nginx.conf`
  (padrão: 1 GB).
- **Timeouts para arquivos grandes:** `proxy_read_timeout`/`proxy_send_timeout`
  no Nginx e `--timeout` no Gunicorn (padrão: 600 s).
- **Variáveis de ambiente da app:** `/opt/json2cnab750/.env`.
