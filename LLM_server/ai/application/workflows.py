"""
LLM 애플리케이션 워크플로우 - 단순화된 최적화 버전
LLM 처리 전체 플로우와 외부 통신 관리
"""
import logging
import sys
import os
import time
import concurrent.futures
from typing import Dict, Any
from django.conf import settings
from django.core.cache import cache

# 공통 HTTP 클라이언트 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
try:
    from shared.infrastructure.http_client import http_client
except ImportError:
    # 공통 클라이언트를 찾을 수 없는 경우 requests 직접 사용
    import requests
    http_client = None

from ..domain.services import llm_domain_service

logger = logging.getLogger(__name__)

class LLMWorkflowService:
    """LLM 워크플로우 서비스 - 단순화된 최적화"""

    def __init__(self):
        self.domain_service = llm_domain_service
        self.tts_server_url = getattr(settings, 'TTS_SERVER_URL', 'http://tts_server:5002')

    def process_text_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 요청 처리 - 단순화된 워크플로우"""
        try:
            print("🔥" * 20)
            print("📨 [LLM Workflow] STT에서 텍스트 수신!")
            print("🔥" * 20)
            print(f"📝 텍스트: {request_data.get('text', '')}")
            print(f"📱 전화번호: {request_data.get('phoneId', 'N/A')}")
            print(f"🆔 세션 ID: {request_data.get('sessionId', 'N/A')}")
            print(f"🔑 요청 ID: {request_data.get('requestId', 'N/A')}")

            total_start_time = time.time()

            # 1. 데이터 유효성 검증
            validation_result = self.domain_service.validate_text_request(request_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'stage': 'validation'
                }

            user_text = request_data.get('text', '')
      
            phone_id = request_data.get('phoneId', '')
      

            # 2. Weaviate 저장만 백그라운드에서 처리 (최적화 유지)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                # 3. LLM 처리 (메인 작업)
                llm_start_time = time.time()
                llm_result = self.domain_service.process_text_with_llm(phone_id, user_text)
                llm_elapsed = time.time() - llm_start_time
                print(f"⚡ LLM 처리 시간: {llm_elapsed:.4f}초")

                if not llm_result['success']:
                    return {
                        'success': False,
                        'error': llm_result['error'],
                        'stage': 'llm_processing'
                    }

                # 4. TTS 메시지 생성 (단순화)
                tts_message = {
                    'phoneId': request_data.get('phoneId', ''),
                    'sessionId': request_data.get('sessionId', ''),
                    'requestId': request_data.get('requestId', ''),
                    'timestamp': request_data.get('timestamp', ''),
                    'voice_config': {'language': 'ko', 'speed': 1.0},
                    'text': llm_result['llm_response']
                }

                print(f"🤖 [LLM Workflow] LLM 응답: '{llm_result['llm_response']}'")
                print(f"📦 [LLM Workflow] TTS 서버로 전송할 메시지: {tts_message}")

                # 5. TTS 서버로 전송
                send_result = self.send_to_tts_server(tts_message)


            total_elapsed = time.time() - total_start_time
            print(f"🚀 [최적화] 전체 처리 시간: {total_elapsed:.4f}초")

            return {
                'success': send_result['success'],
                'llm_response': llm_result['llm_response'],
                'processing_time': llm_result['processing_time'],
                'tts_response': send_result,
                'total_time': total_elapsed,
                'stage': 'completed'
            }

        except Exception as e:
            logger.error(f"❌ [LLM Workflow] 워크플로우 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'workflow_error'
            }

    def _save_to_weaviate_async(self, request_data: Dict[str, Any]) -> bool:
        """Weaviate 저장을 비동기로 처리 (유일한 백그라운드 작업)"""
        try:
            self.domain_service.save_to_weaviate(request_data)
            return True
        except Exception as e:
            logger.warning(f"⚠️ [비동기] Weaviate 저장 실패: {e}")
            return False

    def send_to_tts_server(self, tts_message: Dict[str, Any]) -> Dict[str, Any]:
        """TTS 서버로 HTTP POST 전송"""
        try:
            tts_url = f"{self.tts_server_url}/api/convert-tts/"
            print(f"📤 [LLM Workflow] TTS 서버로 HTTP 전송: {tts_url}")

            if http_client:
                response = http_client.post(tts_url, tts_message)
                return response
            else:
                import requests
                response = requests.post(tts_url, json=tts_message, timeout=30, verify=False)

                if response.status_code == 200:
                    print("✅ [LLM Workflow] TTS 서버로 전송 성공!")
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'data': response.json() if response.content else None
                    }
                else:
                    print(f"❌ [LLM Workflow] TTS 서버 전송 실패: {response.status_code}")
                    return {
                        'success': False,
                        'status_code': response.status_code,
                        'error': response.text
                    }

        except Exception as e:
            logger.error(f"❌ [LLM Workflow] TTS 서버 전송 오류: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# 싱글톤 인스턴스
llm_workflow_service = LLMWorkflowService()
