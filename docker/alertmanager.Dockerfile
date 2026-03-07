FROM prom/alertmanager:latest
COPY alertmanager.yml /etc/alertmanager/alertmanager.yml
COPY docker/alertmanager-entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER nobody
ENTRYPOINT ["/entrypoint.sh"]
