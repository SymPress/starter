FROM docker.io/ddev/ddev-webserver:v1.25.4
USER root
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server mariadb-server acl sudo libfcgi-bin \
    && rm -rf /var/lib/apt/lists/* && update-alternatives --set php /usr/bin/php8.5
ENV COMPOSER_ALLOW_SUPERUSER=1
ENV SYMPRESS_DISPOSABLE_DEPLOY_HOST=1
WORKDIR /workspace
ENTRYPOINT ["bash", "-lc"]
