#!/usr/bin/env bash
# Pull new code from GitHub; restart only when something changed.
set -e
cd /opt/estatehawk
git fetch -q origin
LOCAL=$(git rev-parse HEAD); REMOTE=$(git rev-parse @{u})
[ "$LOCAL" = "$REMOTE" ] && exit 0
OLDREQ=$(git show HEAD:requirements.txt | md5sum)
git pull -q --ff-only
[ "$OLDREQ" = "$(md5sum < requirements.txt)" ] || .venv/bin/pip install -q -r requirements.txt
sudo /usr/bin/systemctl restart estatehawk
echo "$(date '+%F %T') updated to $(git rev-parse --short HEAD)" >> data/deploy.log
