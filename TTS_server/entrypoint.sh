#!/bin/bash

# TTS 서버 엔트리포인트 스크립트
echo "🚀 TTS 서버 초기화"

# NLTK 데이터 다운로드 (필요한 경우)
python -c "
import nltk
import os

# NLTK 데이터 경로 설정
nltk_data_dir = '/usr/share/nltk_data'
os.makedirs(nltk_data_dir, exist_ok=True)

print('📥 NLTK 데이터 다운로드...')
try:
    nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_dir)
    nltk.download('averaged_perceptron_tagger_eng', download_dir=nltk_data_dir)
    nltk.download('punkt', download_dir=nltk_data_dir)
    nltk.download('punkt_tab', download_dir=nltk_data_dir)
    nltk.download('maxent_ne_chunker', download_dir=nltk_data_dir)
    nltk.download('words', download_dir=nltk_data_dir)
    nltk.download('cmudict', download_dir=nltk_data_dir)
    print('✅ NLTK 데이터 다운로드 완료')
except Exception as e:
    print(f'⚠️ NLTK 데이터 다운로드 오류: {e}')
"

# 환경 변수 설정
export PYTHONUNBUFFERED=1
export DJANGO_SETTINGS_MODULE=TTS_server.settings
export NLTK_DATA=/usr/share/nltk_data

echo "🔌 Daphne ASGI 서버 시작 (포트 5002)"
echo "   - HTTP 엔드포인트: http://0.0.0.0:5002/api/"
echo "   - WebSocket 엔드포인트: ws://0.0.0.0:5002/ws/tts/"

# Daphne 실행 (HTTP와 WebSocket 모두 처리)
exec daphne -b 0.0.0.0 -p 5002 --verbosity 2 TTS_server.asgi:application