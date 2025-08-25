#!/bin/bash
set -e

# Uvicorn 직접 사용 (로깅 활성화)
start_uvicorn_direct() {
    echo "Starting with Uvicorn directly for faster reload..."

    export PYTHONUNBUFFERED=1
    export DJANGO_DEBUG=True
    export DJANGO_SETTINGS_MODULE=LLM_server.settings
    export DJANGO_LOG_LEVEL=INFO

    cd /code

    # Python 모듈로 uvicorn 실행 (PATH 문제 방지)
    exec python -m uvicorn LLM_server.asgi:application \
        --host 0.0.0.0 \
        --port 5000 \
        --reload \
        --reload-dir /code/ \
        --log-level info \
        --access-log \
        --use-colors
}

# 실행
start_uvicorn_direct
