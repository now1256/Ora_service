#!/bin/bash

# HTTP와 WebSocket 서버를 모두 시작하는 스크립트
echo "🚀 TTS 서버 시작"

# 환경 변수 설정
export PYTHONUNBUFFERED=1
export DJANGO_DEBUG=True
export DJANGO_SETTINGS_MODULE=TTS_server.settings
export DJANGO_LOG_LEVEL=INFO

# HTTP 서버 (포트 5001)
echo "📡 HTTP 서버 시작 (포트 5001)"
gunicorn TTS_server.wsgi:application \
    --bind 0.0.0.0:5001 \
    --workers 2 \
    --threads 4 \
    --worker-class sync \
    --timeout 600 \
    --log-level info \
    --access-logfile - \
    --error-logfile - &

# WebSocket 서버 (포트 5002)
echo "🔌 WebSocket 서버 시작 (포트 5002)"
daphne -b 0.0.0.0 -p 5002 --verbosity 2 TTS_server.asgi:application &

# 두 프로세스가 모두 실행되도록 대기
wait