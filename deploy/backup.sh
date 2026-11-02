#!/usr/bin/env bash
# Daily copy of the database (keeps 14 days).
set -e
mkdir -p ~/estatehawk-backups
sqlite3 /opt/estatehawk/data/estatehawk.db ".backup '$HOME/estatehawk-backups/estatehawk-$(date +%F).db'"
ls -1t ~/estatehawk-backups/*.db | tail -n +15 | xargs -r rm --
