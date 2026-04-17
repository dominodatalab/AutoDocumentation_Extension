#!/usr/bin/env bash
set -eu

pip install --no-cache-dir \
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
