"""
LLM 인터페이스 시리얼라이저
요청/응답 데이터 검증 및 변환
"""
from rest_framework import serializers
from typing import Dict, Any

class TextProcessRequestSerializer(serializers.Serializer):
    """텍스트 처리 요청 데이터 검증"""
    text = serializers.CharField(required=True, max_length=5000, help_text="처리할 텍스트")
    phoneId = serializers.CharField(required=True, max_length=20, help_text="전화번호")
    sessionId = serializers.CharField(required=True, max_length=50, help_text="세션 ID")
    requestId = serializers.CharField(required=True, max_length=50, help_text="요청 ID")
    source = serializers.CharField(required=False, max_length=50, default="STT_server", help_text="요청 소스")
    timestamp = serializers.CharField(required=False, help_text="타임스탬프")
    request_type = serializers.CharField(required=False, default="speech_to_text_completed", help_text="요청 타입")
    
    def validate_text(self, value):
        """텍스트 내용 검증 - 실시간 대화용으로 완화"""
        if not value.strip():
            raise serializers.ValidationError("텍스트가 비어있습니다.")
        # 🔧 실시간 대화에서 "네", "끝" 같은 1글자도 허용
        if len(value.strip()) < 1:
            raise serializers.ValidationError("텍스트가 비어있습니다.")
        return value.strip()

class SimpleLLMRequestSerializer(serializers.Serializer):
    """간단한 LLM 요청 데이터 검증"""
    phone_id = serializers.CharField(required=True, max_length=20, help_text="전화번호")
    text = serializers.CharField(required=True, max_length=5000, help_text="처리할 텍스트")

class LLMResponseSerializer(serializers.Serializer):
    """LLM 응답 데이터 구조"""
    success = serializers.BooleanField(help_text="처리 성공 여부")
    llm_response = serializers.CharField(required=False, help_text="LLM 생성 응답")
    processing_time = serializers.FloatField(required=False, help_text="처리 시간(초)")
    error = serializers.CharField(required=False, help_text="오류 메시지")
    stage = serializers.CharField(required=False, help_text="처리 단계")
    tts_response = serializers.DictField(required=False, help_text="TTS 서버 응답")

class ServerInfoSerializer(serializers.Serializer):
    """서버 정보 구조"""
    server = serializers.CharField(help_text="서버 이름")
    version = serializers.CharField(help_text="버전")
    port = serializers.IntegerField(help_text="포트 번호")
    status = serializers.CharField(help_text="서버 상태")
    architecture = serializers.CharField(help_text="아키텍처")
    description = serializers.CharField(help_text="서버 설명")
    endpoints = serializers.DictField(help_text="사용 가능한 엔드포인트") 