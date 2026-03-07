#!/bin/sh
set -e

CONFIG_FILE="/etc/prometheus/prometheus.yml"

if [ -n "$METRICS_TOKEN" ]; then
    sed -i "s/__METRICS_TOKEN__/$METRICS_TOKEN/g" "$CONFIG_FILE"
else
    echo "WARNING: METRICS_TOKEN not set, metrics endpoints will use placeholder credentials"
fi

exec /bin/prometheus "$@"
