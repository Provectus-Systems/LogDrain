FROM prom/prometheus:latest
USER root
COPY prometheus.yml /etc/prometheus/prometheus.yml
COPY alert_rules.yml /etc/prometheus/alert_rules.yml
COPY docker/prometheus-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R nobody:nobody /etc/prometheus
USER nobody
ENTRYPOINT ["/entrypoint.sh"]
