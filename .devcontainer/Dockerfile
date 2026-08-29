FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG QUARTO_VERSION=1.10.18

ENV DEBIAN_FRONTEND=noninteractive
ENV SIGIL_SYSTEM_MODE=thin
ENV SIGIL_QUARTO_ACTIONS_HOME=/workspace/sigil-quarto-actions
ENV SIGILBOOK_PATH=/workspace/sigilbook

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        pandoc \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL \
        "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.deb" \
        -o /tmp/quarto.deb \
    && apt-get update \
    && apt-get install -y /tmp/quarto.deb \
    && rm -f /tmp/quarto.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/sigil-quarto-actions
