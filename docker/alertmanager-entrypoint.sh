#!/bin/sh
set -e

CONFIG_FILE="/etc/alertmanager/alertmanager.yml"

if [ -n "$SMTP_PASSWORD" ]; then
    sed -i "s/__SMTP_PASSWORD__/$SMTP_PASSWORD/g" "$CONFIG_FILE"
else
    echo "WARNING: SMTP_PASSWORD not set, email alerts will not work"
fi

exec /bin/alertmanager "$@"
