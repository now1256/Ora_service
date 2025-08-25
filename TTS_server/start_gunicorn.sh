#!/bin/bash
set -e

# Django runserver 사용 (안정적인 방법)
start_django_runserver() {
    echo "Starting with Django runserver for stability..."

    export PYTHONUNBUFFERED=1
    export DJANGO_DEBUG=True
    export DJANGO_SETTINGS_MODULE=TTS_server.settings
    export DJANGO_LOG_LEVEL=INFO

    cd /code
    
    # Django의 기본 runserver 사용 (uvicorn 없이도 작동)
    python manage.py runserver 0.0.0.0:5002
}

# 실행
start_django_runserver
