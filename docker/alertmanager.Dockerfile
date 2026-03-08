FROM prom/alertmanager:latest
USER root
COPY alertmanager.yml /etc/alertmanager/alertmanager.yml
COPY docker/alertmanager-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R nobody:nobody /etc/alertmanager
USER nobody
ENTRYPOINT ["/entrypoint.sh"]
CMD ["--config.file=/etc/alertmanager/alertmanager.yml"]
