FROM grafana/loki:2.9.0
COPY loki-config.yml /etc/loki/local-config.yaml
