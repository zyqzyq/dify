# base image
FROM python:3.12-slim-bookworm AS base

WORKDIR /app/api

# Install uv
ENV UV_VERSION=0.8.9

# PyPI mirror for pip only. Do not set UV_DEFAULT_INDEX: Aliyun (or any non-default index) makes
# `uv sync --locked` reject the repo lockfile, which is generated against PyPI.
ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

RUN pip install --no-cache-dir -i "${PYPI_INDEX_URL}" uv==${UV_VERSION}


FROM base AS packages

ARG APT_DEBIAN_MIRROR=mirrors.aliyun.com

RUN set -eux \
    && if [ "${APT_DEBIAN_MIRROR}" != "deb.debian.org" ]; then \
        sed -i "s@deb.debian.org@${APT_DEBIAN_MIRROR}@g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
          # basic environment
          g++ \
          # for building gmpy2
          libmpfr-dev libmpc-dev

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# production stage
FROM base AS production

ENV FLASK_APP=app.py
ENV EDITION=SELF_HOSTED
ENV DEPLOY_ENV=PRODUCTION
ENV CONSOLE_API_URL=http://127.0.0.1:5001
ENV CONSOLE_WEB_URL=http://127.0.0.1:3000
ENV SERVICE_API_URL=http://127.0.0.1:5001
ENV APP_WEB_URL=http://127.0.0.1:3000

EXPOSE 5001

# set timezone
ENV TZ=UTC

# Set UTF-8 locale
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV PYTHONIOENCODING=utf-8

WORKDIR /app/api

# Create non-root user
ARG dify_uid=1001
ARG NODE_MAJOR=22
ARG NODE_PACKAGE_VERSION=22.21.0-1nodesource1
ARG NODESOURCE_KEY_FPR=6F71F525282841EEDAF851B42F59B5F99B1BE0B4
ARG APT_DEBIAN_MIRROR=mirrors.aliyun.com
ARG NODESOURCE_BASE_URL=https://deb.nodesource.com
ARG NLTK_INDEX_XML_URL=https://cdn.jsdelivr.net/gh/nltk/nltk_data@gh-pages/index.xml
ARG NLTK_PACKAGE_URL_PREFIX=https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/
ARG NLTK_PACKAGE_URL_REPLACEMENT=https://cdn.jsdelivr.net/gh/nltk/nltk_data@gh-pages/
RUN groupadd -r -g ${dify_uid} dify && \
    useradd -r -u ${dify_uid} -g ${dify_uid} -s /bin/bash dify && \
    chown -R dify:dify /app

RUN \
    set -eux \
    && if [ "${APT_DEBIAN_MIRROR}" != "deb.debian.org" ]; then \
        sed -i "s@deb.debian.org@${APT_DEBIAN_MIRROR}@g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL "${NODESOURCE_BASE_URL}/gpgkey/nodesource-repo.gpg.key" -o /tmp/nodesource.gpg \
    && gpg --show-keys --with-colons /tmp/nodesource.gpg \
        | awk -F: '/^fpr:/ {print $10}' \
        | grep -Fx "${NODESOURCE_KEY_FPR}" \
    && gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg /tmp/nodesource.gpg \
    && rm -f /tmp/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] ${NODESOURCE_BASE_URL}/node_${NODE_MAJOR}.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    # Install dependencies
    && apt-get install -y --no-install-recommends \
        # basic environment
        nodejs=${NODE_PACKAGE_VERSION} \
        # for gmpy2 \
        libgmp-dev libmpfr-dev libmpc-dev \
        # For Security
        expat libldap-2.5-0=2.5.13+dfsg-5 perl libsqlite3-0=3.40.1-2+deb12u2 zlib1g=1:1.2.13.dfsg-1 \
        # install fonts to support the use of tools like pypdfium2
        fonts-noto-cjk \
        # install a package to improve the accuracy of guessing mime type and file extension
        media-types \
        # install libmagic to support the use of python-magic guess MIMETYPE
        libmagic1 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy Python environment and packages
ENV VIRTUAL_ENV=/app/api/.venv
COPY --from=packages --chown=dify:dify ${VIRTUAL_ENV} ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Download nltk data (NLTK_* build args above; patches nltk.download for unstructured)
COPY docker/bootstrap_nltk_mirror.py /tmp/bootstrap_nltk_mirror.py
RUN mkdir -p /usr/local/share/nltk_data \
    && NLTK_DATA=/usr/local/share/nltk_data \
        NLTK_INDEX_XML_URL="${NLTK_INDEX_XML_URL}" \
        NLTK_PACKAGE_URL_PREFIX="${NLTK_PACKAGE_URL_PREFIX}" \
        NLTK_PACKAGE_URL_REPLACEMENT="${NLTK_PACKAGE_URL_REPLACEMENT}" \
        python /tmp/bootstrap_nltk_mirror.py \
    && rm -f /tmp/bootstrap_nltk_mirror.py \
    && chmod -R 755 /usr/local/share/nltk_data

ENV TIKTOKEN_CACHE_DIR=/app/api/.tiktoken_cache

RUN python -c "import tiktoken; tiktoken.encoding_for_model('gpt2')" \
    && chown -R dify:dify ${TIKTOKEN_CACHE_DIR}

# Copy source code
COPY --chown=dify:dify . /app/api/

# Prepare entrypoint script
COPY --chown=dify:dify --chmod=755 docker/entrypoint.sh /entrypoint.sh


ARG COMMIT_SHA
ENV COMMIT_SHA=${COMMIT_SHA}
ENV NLTK_DATA=/usr/local/share/nltk_data

USER dify

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
