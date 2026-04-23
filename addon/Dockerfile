ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apk add --no-cache python3 py3-pip

WORKDIR /opt/infinitude-proxy

COPY pyproject.toml ./
COPY src/ ./src/
COPY log_config.yaml ./

RUN pip install --no-cache-dir --break-system-packages .

COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 3001

CMD ["/run.sh"]
