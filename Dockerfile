LABEL maintainer="Domino Data Lab"
LABEL description="Auto Model Docs extension environment for Domino Data Lab"
ARG EXTENSION_VERSION=main
LABEL version=$EXTENSION_VERSION

ARG GITHUB_ORG=dominodatalab
ARG GITHUB_USERNAME=
ARG GITHUB_PAT=
ARG DUSER=ubuntu
ARG DGROUP=ubuntu
ARG DEBIAN_FRONTEND=noninteractive

ENV DOMINO_USER=$DUSER
ENV DOMINO_GROUP=$DGROUP
ENV APP_WORK_DIR="/home/$DOMINO_USER"
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

USER root

RUN apt-get update \
  && apt-get install -y --no-install-recommends git ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p "/home/$DOMINO_USER"

# Ensure the DOMINO_USER/DOMINO_GROUP exists inside the container.
RUN if ! id 12574 >/dev/null 2>&1; then \
        groupadd -g 12574 ${DOMINO_GROUP}; \
        useradd -u 12574 -g 12574 -m -N -s /bin/bash ${DOMINO_USER}; \
    fi

RUN chown -R ${DOMINO_USER}:${DOMINO_GROUP} "/home/${DOMINO_USER}"


# Cleanup after apt package installs
RUN rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_WORK_DIR}

USER $DOMINO_USER

RUN set -eu; \
    REPO_URL="https://github.com/${GITHUB_ORG}/AutoDocumentation_Extension.git"; \
    if [ -n "${GITHUB_USERNAME}" ] && [ -n "${GITHUB_PAT}" ]; then \
      git clone "https://${GITHUB_USERNAME}:${GITHUB_PAT}@github.com/${GITHUB_ORG}/AutoDocumentation_Extension.git" .; \
    else \
      git clone "${REPO_URL}" .; \
    fi; \
    git checkout "${EXTENSION_VERSION}"

RUN chmod +x ./app.sh && chmod +x ./setup-deps.sh && chmod +x ./auto_model_docs/app_studio.sh
RUN ./setup-deps.sh
