LABEL maintainer="Domino Data Lab"
LABEL description="Auto Model Docs extension environment for Domino Data Lab"
ARG EXTENSION_VERSION=main
LABEL version=$EXTENSION_VERSION

ARG GITHUB_ORG=dominodatalab
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
  && apt-get install -y --no-install-recommends git ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p $APP_WORK_DIR

# Ensure the DOMINO_USER/DOMINO_GROUP exists inside the container.
RUN if ! id 12574 >/dev/null 2>&1; then \
        groupadd -g 12574 ${DOMINO_GROUP}; \
        useradd -u 12574 -g 12574 -m -N -s /bin/bash ${DOMINO_USER}; \
    fi

RUN chown -R ${DOMINO_USER}:${DOMINO_GROUP} $APP_WORK_DIR


# Cleanup after apt package installs
RUN rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_WORK_DIR}

USER $DOMINO_USER

RUN set -eu; \
    git clone "https://github.com/${GITHUB_ORG}/AutoDocumentation_Extension.git" .; \
    git checkout "${EXTENSION_VERSION}"

RUN chmod +x ./app.sh && chmod +x ./setup-deps.sh && chmod +x ./auto_model_docs/app_studio.sh && chmod +x ./cli.sh
RUN ./setup-deps.sh
