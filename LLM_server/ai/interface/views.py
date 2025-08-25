"""
LLM 인터페이스 뷰
요청/응답 처리만 담당하는 간소화된 뷰
"""
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json

from ..application.workflows import llm_workflow_service
from .serializers import TextProcessRequestSerializer, SimpleLLMRequestSerializer, LLMResponseSerializer, ServerInfoSerializer

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
def process_text(request):
    """STT에서 텍스트를 받아 LangChain 처리 후 TTS로 전송하는 HTTP 엔드포인트"""
    try:
        print("🔥" * 30)
        print("📨 [LLM View] STT에서 요청 수신!")
        print("🔥" * 30)
        print(f"📦 [LLM View] 요청 데이터: {request.data}")
        print(f"📦 [LLM View] 요청 헤더: {dict(request.headers)}")
        
        # 요청 데이터 검증
        serializer = TextProcessRequestSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"❌ [LLM View] 데이터 검증 실패: {serializer.errors}")
            return Response({
                'success': False,
                'error': 'Invalid request data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        print(f"✅ [LLM View] 데이터 검증 성공: {serializer.validated_data}")
        
        # 워크플로우 서비스로 처리 위임
        print("🔄 [LLM View] 워크플로우 서비스 호출 시작...")
        result = llm_workflow_service.process_text_request(serializer.validated_data)
        print(f"✅ [LLM View] 워크플로우 서비스 결과: {result}")

        # 응답 직렬화
        response_serializer = LLMResponseSerializer(data=result)
        if response_serializer.is_valid():
            if result['success']:
                print(f"🎉 [LLM View] 성공 응답 반환: {response_serializer.validated_data}")
                return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
            else:
                print(f"❌ [LLM View] 실패 응답 반환: {response_serializer.validated_data}")
                return Response(response_serializer.validated_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f"⚠️ [LLM View] 응답 시리얼라이저 검증 실패, 원본 결과 반환: {result}")
            return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        print(f"💥 [LLM View] 예외 발생: {e}")
        logger.error(f"❌ [LLM View] 텍스트 처리 오류: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e),
            'stage': 'view_error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
