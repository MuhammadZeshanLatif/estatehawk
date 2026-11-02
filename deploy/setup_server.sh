#!/usr/bin/env bash
# EstateHawk server setup for Ubuntu 22.04/24.04 (Oracle Cloud Always Free, ARM or AMD).
# Run once on the server:   bash setup_server.sh <github-repo-ssh-url> <site-name>
# Example:                  bash setup_server.sh git@github.com:MuhammadZeshanLatif/estatehawk.git estatehawk.duckdns.org
# The DuckDNS token is asked on screen (it is never stored in GitHub).
set -euo pipefail
REPO="${1:?GitHub repo SSH url}"
SITE="${2:?site name, e.g. estatehawk.duckdns.org}"
APP=/opt/estatehawk
U=$(whoami)

echo "== packages"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git sqlite3 curl
sudo timedatectl set-timezone Asia/Karachi   # the app's daily sync time is Pakistan time

echo "== deploy key (read-only access to the private repo)"
mkdir -p ~/.ssh && chmod 700 ~/.ssh
if [ ! -f ~/.ssh/estatehawk_deploy ]; then
  ssh-keygen -t ed25519 -N "" -f ~/.ssh/estatehawk_deploy -C "estatehawk-server"
fi
cat > ~/.ssh/config <<CFG
Host github.com
  IdentityFile ~/.ssh/estatehawk_deploy
  StrictHostKeyChecking accept-new
CFG
chmod 600 ~/.ssh/config
if ! ssh -o BatchMode=yes -T git@github.com 2>&1 | grep -qi "successfully authenticated"; then
  echo
  echo "Add this key in GitHub: repo > Settings > Deploy keys > Add deploy key (read only):"
  cat ~/.ssh/estatehawk_deploy.pub
  read -rp "Press Enter after adding it... "
fi

echo "== code"
sudo mkdir -p $APP && sudo chown "$U:$U" $APP
if [ ! -d $APP/.git ]; then git clone "$REPO" $APP; else git -C $APP pull --ff-only; fi
cd $APP
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
mkdir -p data
[ -f .env ] || cp .env.example .env
grep -q '^SECRET_KEY=' .env || echo "SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')" >> .env

echo "== app service"
sudo tee /etc/systemd/system/estatehawk.service >/dev/null <<SVC
[Unit]
Description=EstateHawk
After=network-online.target
[Service]
User=$U
WorkingDirectory=$APP
ExecStart=$APP/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
SVC

echo "== auto update from GitHub every 2 minutes + daily backup"
chmod +x $APP/deploy/update.sh $APP/deploy/backup.sh
sudo tee /etc/systemd/system/estatehawk-update.service >/dev/null <<SVC
[Unit]
Description=EstateHawk pull from GitHub
[Service]
Type=oneshot
User=$U
ExecStart=$APP/deploy/update.sh
SVC
sudo tee /etc/systemd/system/estatehawk-update.timer >/dev/null <<SVC
[Unit]
Description=EstateHawk update check
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
[Install]
WantedBy=timers.target
SVC
echo "$U ALL=(root) NOPASSWD: /usr/bin/systemctl restart estatehawk" | sudo tee /etc/sudoers.d/estatehawk >/dev/null
( crontab -l 2>/dev/null | grep -v estatehawk/deploy/backup.sh; echo "30 3 * * * $APP/deploy/backup.sh" ) | crontab -

sudo systemctl daemon-reload
sudo systemctl enable --now estatehawk estatehawk-update.timer

echo "== open web ports 80/443 on the server firewall (also add them in Oracle: VCN > Security List > Ingress)"
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || true
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent && sudo netfilter-persistent save || true

echo "== DuckDNS (keeps $SITE pointing at this server)"
if [[ "$SITE" == *.duckdns.org ]]; then
  SUB=${SITE%%.duckdns.org}
  if [ ! -f ~/.duckdns_token ]; then
    read -rsp "Paste your DuckDNS token (from duckdns.org, top of the page): " TOK; echo
    echo "$TOK" > ~/.duckdns_token; chmod 600 ~/.duckdns_token
  fi
  cat > ~/duckdns.sh <<DD
#!/usr/bin/env bash
curl -fsS "https://www.duckdns.org/update?domains=$SUB&token=\$(cat ~/.duckdns_token)&ip=" -o ~/duckdns.log
DD
  chmod +x ~/duckdns.sh && ~/duckdns.sh && echo "DuckDNS: $(cat ~/duckdns.log)"
  ( crontab -l 2>/dev/null | grep -v duckdns.sh; echo "*/5 * * * * $HOME/duckdns.sh" ) | crontab -
fi

echo "== Caddy (free HTTPS certificate, renews by itself)"
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https gnupg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
sudo apt-get update -y && sudo apt-get install -y caddy
sudo tee /etc/caddy/Caddyfile >/dev/null <<CF
$SITE {
  encode gzip
  reverse_proxy 127.0.0.1:8000
}
CF
sudo systemctl reload caddy || sudo systemctl restart caddy

sleep 3
curl -s -o /dev/null -w "local check: HTTP %{http_code}\n" http://127.0.0.1:8000/api/auth/me || true
echo "Done. Open https://$SITE and create the admin account. Put GEMINI_API_KEY in $APP/.env, then: sudo systemctl restart estatehawk"
