#!/usr/bin/env bash
# EstateHawk server setup for Ubuntu 22.04/24.04 (Oracle Cloud Always Free, ARM or AMD).
# Run once on the server:   bash setup_server.sh <github-repo-ssh-url> <cloudflare-tunnel-token>
# Example:                  bash setup_server.sh git@github.com:Arius-Automation/estatehawk.git eyJhIjoi...
set -euo pipefail
REPO="${1:?GitHub repo SSH url}"
CF_TOKEN="${2:-}"
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

echo "== Cloudflare tunnel"
if [ -n "$CF_TOKEN" ]; then
  ARCH=$(dpkg --print-architecture)
  curl -fsSL -o /tmp/cloudflared.deb "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$ARCH.deb"
  sudo dpkg -i /tmp/cloudflared.deb
  sudo cloudflared service install "$CF_TOKEN" || true
fi

sleep 3
curl -s -o /dev/null -w "local check: HTTP %{http_code}\n" http://127.0.0.1:8000/api/auth/me || true
echo "Done. Open your domain and create the admin account. Put GEMINI_API_KEY in $APP/.env, then: sudo systemctl restart estatehawk"
