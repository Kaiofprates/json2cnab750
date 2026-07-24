#!/usr/bin/env bash
#
# Deploy da API + site JSON2CNAB750 em um VPS Hostinger (Ubuntu/Debian).
#
# É idempotente: na primeira execução provisiona tudo (pacotes, usuário,
# venv, systemd, nginx); nas seguintes apenas atualiza o código e reinicia.
#
# USO (como root, no VPS):
#   SERVER_NAME=meudominio.com.br ./deploy.sh
#
# Variáveis de ambiente (todas opcionais, exceto quando indicado):
#   SERVER_NAME   Domínio/host do site           (padrão: _  => qualquer host)
#   REPO_URL      URL do repositório git          (padrão: repo público do projeto)
#   BRANCH        Branch a implantar              (padrão: main)
#   APP_USER      Usuário de sistema da app       (padrão: json2cnab)
#   APP_DIR       Diretório de instalação         (padrão: /opt/json2cnab750)
#   PYTHON        Interpretador Python base       (padrão: python3)
#   SKIP_APT=1    Pula a instalação de pacotes do sistema (updates rápidos)
#   RUN_CERTBOT=1 Emite certificado HTTPS via certbot ao final
#
set -euo pipefail

# ------------------------------------------------------------------ #
# Configuração                                                        #
# ------------------------------------------------------------------ #
SERVER_NAME="${SERVER_NAME:-_}"
REPO_URL="${REPO_URL:-https://github.com/kaiofprates/json2cnab750.git}"
BRANCH="${BRANCH:-main}"
APP_USER="${APP_USER:-json2cnab}"
APP_DIR="${APP_DIR:-/opt/json2cnab750}"
PYTHON="${PYTHON:-python3}"
SKIP_APT="${SKIP_APT:-0}"
RUN_CERTBOT="${RUN_CERTBOT:-0}"

SERVICE_NAME="json2cnab750"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[erro]\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "Execute como root (use sudo)."

# ------------------------------------------------------------------ #
# 1. Pacotes de sistema                                               #
# ------------------------------------------------------------------ #
if [ "$SKIP_APT" != "1" ]; then
  log "Instalando pacotes de sistema…"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq \
    "$PYTHON" python3-venv python3-pip \
    git nginx ca-certificates
  if [ "$RUN_CERTBOT" = "1" ]; then
    apt-get install -y -qq certbot python3-certbot-nginx
  fi
else
  log "SKIP_APT=1 — pulando instalação de pacotes."
fi

# ------------------------------------------------------------------ #
# 2. Usuário de sistema                                               #
# ------------------------------------------------------------------ #
if ! id "$APP_USER" >/dev/null 2>&1; then
  log "Criando usuário de sistema '$APP_USER'…"
  useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
else
  log "Usuário '$APP_USER' já existe."
fi

# ------------------------------------------------------------------ #
# 3. Código-fonte (clone ou atualização)                             #
# ------------------------------------------------------------------ #
if [ -d "$APP_DIR/.git" ]; then
  log "Atualizando repositório em $APP_DIR (branch $BRANCH)…"
  sudo -u "$APP_USER" git -C "$APP_DIR" fetch --depth 1 origin "$BRANCH"
  sudo -u "$APP_USER" git -C "$APP_DIR" checkout -B "$BRANCH" "origin/$BRANCH"
else
  log "Clonando $REPO_URL em $APP_DIR…"
  mkdir -p "$APP_DIR"
  chown "$APP_USER:$APP_USER" "$APP_DIR"
  sudo -u "$APP_USER" git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

# ------------------------------------------------------------------ #
# 4. Ambiente virtual + dependências                                 #
# ------------------------------------------------------------------ #
if [ ! -d "$APP_DIR/venv" ]; then
  log "Criando ambiente virtual…"
  sudo -u "$APP_USER" "$PYTHON" -m venv "$APP_DIR/venv"
fi
log "Instalando dependências Python…"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade -q pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q \
  -r "$APP_DIR/requirements.txt" \
  -r "$APP_DIR/requirements-prod.txt"

# ------------------------------------------------------------------ #
# 5. Arquivo .env (criado uma vez; editável depois)                  #
# ------------------------------------------------------------------ #
if [ ! -f "$APP_DIR/.env" ]; then
  log "Criando $APP_DIR/.env padrão…"
  cat > "$APP_DIR/.env" <<EOF
APP_NAME=JSON2CNAB750
DEBUG=false
EOF
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
fi

# ------------------------------------------------------------------ #
# 6. Serviço systemd                                                  #
# ------------------------------------------------------------------ #
log "Instalando unidade systemd '$SERVICE_NAME'…"
sed \
  -e "s|__APP_USER__|$APP_USER|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  "$SCRIPT_DIR/json2cnab750.service" \
  > "/etc/systemd/system/${SERVICE_NAME}.service"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
systemctl restart "$SERVICE_NAME"

# ------------------------------------------------------------------ #
# 7. Nginx                                                            #
# ------------------------------------------------------------------ #
log "Configurando Nginx para server_name '$SERVER_NAME'…"
sed \
  -e "s|__SERVER_NAME__|$SERVER_NAME|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  "$SCRIPT_DIR/nginx.conf" \
  > "/etc/nginx/sites-available/${SERVICE_NAME}"

ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}" \
       "/etc/nginx/sites-enabled/${SERVICE_NAME}"

# Remove o site default para não competir pelo server_name padrão.
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

# ------------------------------------------------------------------ #
# 8. HTTPS (opcional)                                                 #
# ------------------------------------------------------------------ #
if [ "$RUN_CERTBOT" = "1" ] && [ "$SERVER_NAME" != "_" ]; then
  log "Emitindo certificado HTTPS via certbot…"
  certbot --nginx -d "$SERVER_NAME" --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect || \
    warn "Certbot falhou — verifique DNS/porta 80 e rode manualmente:  certbot --nginx -d $SERVER_NAME"
fi

# ------------------------------------------------------------------ #
# Resumo                                                              #
# ------------------------------------------------------------------ #
log "Deploy concluído."
echo
echo "  Serviço:  systemctl status $SERVICE_NAME"
echo "  Logs:     journalctl -u $SERVICE_NAME -f"
echo "  Site:     http://${SERVER_NAME/_/<IP-ou-domínio>}/"
echo "  API docs: http://${SERVER_NAME/_/<IP-ou-domínio>}/docs"
if [ "$RUN_CERTBOT" != "1" ]; then
  echo
  echo "  Para habilitar HTTPS depois de apontar o DNS:"
  echo "    sudo certbot --nginx -d $SERVER_NAME"
fi
