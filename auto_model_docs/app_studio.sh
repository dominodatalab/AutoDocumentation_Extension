#!/bin/bash

export APP_HOST="0.0.0.0"
export APP_PORT="8888"

export PYTHONPATH="./auto_model_docs:$PYTHONPATH"
export LD_LIBRARY_PATH="/opt/conda/lib:${LD_LIBRARY_PATH:-}"

# Run the FastHTML web app
cd ./auto_model_docs
python web_app_studio.py
