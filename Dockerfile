FROM python:3.10-slim-bullseye


LABEL maintainer="Domino Data Lab"
LABEL description="Auto Model Docs extension environment for Domino Data Lab"
ARG EXTENSION_VERSION=${EXTENSION_VERSION:-main}
LABEL version=$EXTENSION_VERSION

ARG GITHUB_ORG=dominodatalab
ARG GITHUB_USERNAME=
ARG GITHUB_PAT=
ARG DUSER=ubuntu
ARG DGROUP=ubuntu
ARG DEBIAN_FRONTEND=noninteractive

ENV DOMINO_USER=$DUSER
ENV DOMINO_GROUP=$DGROUP


ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends git ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/${DOMINO_USER:-domino}

# Ensure the DOMINO_USER/DOMINO_GROUP exists inside the container.
RUN if ! id 12574 >/dev/null 2>&1; then \
        groupadd -g 12574 ${DOMINO_GROUP}; \
        useradd -u 12574 -g 12574 -m -N -s /bin/bash ${DOMINO_USER}; \
    fi

RUN chown -R ${DOMINO_USER}:${DOMINO_GROUP} "/home/${DOMINO_USER}"

USER root
RUN pip install --no-cache-dir \
    "anthropic==0.84.0" \
    "openai==2.26.0" \
    "mlflow==3.2.0" \
    "python-docx==1.2.0" \
    "matplotlib==3.8.4" \
    "pydantic==2.10.6" \
    "pydantic-settings==2.13.1" \
    "pyyaml==6.0.1" \
    "click==8.3.1" \
    "rich==14.3.3" \
    "aiohttp==3.13.3" \
    "aiofiles==25.1.0" \
    "httpx==0.28.1" \
    "python-fasthtml==0.12.48" \
    "starlette==0.41.3" \
    "dominodatalab==2.0.0" \
    "nbformat==5.10.4" \
    "nbclient==0.10.4" \
    "ipykernel==6.19.4" \
    "pytest==9.0.2" \
    "pytest-asyncio==1.3.0" \
    "mammoth>=1.6.0"


# Cleanup after apt package installs
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /home/${DOMINO_USER:-domino}

USER $DOMINO_USER

RUN set -eu; \
    REPO_URL="https://github.com/${GITHUB_ORG}/AutoDocumentation_Extension.git"; \
    if [ -n "${GITHUB_USERNAME}" ] && [ -n "${GITHUB_PAT}" ]; then \
      git clone "https://${GITHUB_USERNAME}:${GITHUB_PAT}@github.com/${GITHUB_ORG}/AutoDocumentation_Extension.git" .; \
    else \
      git clone "${REPO_URL}" .; \
    fi; \
    git checkout "${EXTENSION_VERSION}"

RUN chmod +x ./app.sh && chmod +x ./auto_model_docs/app_studio.sh

CMD ["./app.sh"]
