#!/bin/bash

# WebSocket 서버 시작 스크립트
echo "🚀 TTS WebSocket 서버 시작 (포트: 5002)"

# 환경 변수 설정
export PYTHONUNBUFFERED=1
export DJANGO_DEBUG=True
export DJANGO_SETTINGS_MODULE=TTS_server.settings
export DJANGO_LOG_LEVEL=INFO

# Daphne로 ASGI 서버 실행 (WebSocket 지원)
# 포트 5002에서 실행
daphne -b 0.0.0.0 -p 5002 TTS_server.asgi:application