"""
🚀 현업 레벨 LLM 도메인 서비스
Cold Start 문제 해결 및 실시간 응답 최적화
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from django.core.cache import cache

# ⚡ 500ms 즉시 응답 시스템 import
from ..utils.LangChain import start_chat
from ..utils.LangChain_streaming import start_chat_optimized
from ..utils.LangChain_ultra_fast import start_chat_ultra_fast
from ..utils.LangChain_vector_first import start_chat_vector_first
from ..utils.LangChain_instant_500ms import start_chat_instant_500ms
from ..ultra_fast_llm import ultra_fast_llm
# from ..weaviate.weaviate_client import weaviate_client
# import weaviate.classes as wvc
from ..utils.LangChain import start_chat

logger = logging.getLogger(__name__)

class LLMDomainService:
    """LLM 도메인 서비스 - 핵심 비즈니스 로직만 담당"""
    
    def __init__(self):
        self.weaviate_client = weaviate_client
    
    def process_text_with_llm(self, phone_id: str, user_text: str) -> Dict[str, Any]:
        """🚀 최적화된 텍스트 LLM 처리 - Cold Start 해결"""
        try:
            start_time = time.time()
            # Redis에 사용자 메시지 임시 저장 (구조화)
            # cache.set(phone_id, {"user_text": user_text}, timeout=300)
            
            logger.info(f"🤖 [LLM Domain] 최적화된 LangChain 처리 시작 - Phone: {phone_id}")
            logger.info(f"📝 [LLM Domain] 입력 텍스트: '{user_text[:50]}...'")
                        
            llm_response = start_chat(phone_id, user_text)

            processing_time = time.time() - start_time
            # ⚡ 500ms 최적화 - 응답이 있으면 무조건 성공 처리
            if llm_response and len(llm_response.strip()) > 0:
                logger.info(f"✅ [LLM Domain] LLM 응답 생성 성공: '{llm_response[:50]}...'")
                logger.info(f"⏱️ [LLM Domain] 총 처리 시간: {processing_time:.3f}초")
                
                return {
                    'success': True,  # 응답이 있으면 무조건 성공
                    'llm_response': llm_response,
                    'processing_time': processing_time,
                    'input_text': user_text,
                    'optimization': 'instant_500ms_cache_system'
                }
            else:
                logger.error(f"❌ [LLM Domain] LLM 응답 생성 실패 또는 빈 응답")
                return {
                    'success': False,
                    'error': 'LLM 응답이 비어있습니다',
                    'processing_time': processing_time,
                    'input_text': user_text
                }
                
        except Exception as e:
            logger.error(f"❌ [LLM Domain] LLM 처리 오류: {e}")
            
            # 🚀 Fallback: 기존 방식으로 재시도
            try:
                logger.info("🔄 [Fallback] 기존 방식으로 재시도")
                fallback_response = start_chat(phone_id, user_text)
                
                if fallback_response:
                    return {
                        'success': True,
                        'llm_response': fallback_response,
                        'processing_time': time.time() - start_time,
                        'input_text': user_text,
                        'optimization': 'fallback_langchain'
                    }
            except Exception as fallback_error:
                logger.error(f"❌ [Fallback] 재시도도 실패: {fallback_error}")
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'input_text': user_text
            }
    
    def save_to_weaviate(self, message_data: Dict[str, Any], consumer_id: str = "http_endpoint") -> bool:
        """Weaviate에 대화 내용 저장"""
        try:
            client = self.weaviate_client.client
            
            # 1. Phone 객체가 존재하는지 확인하고, 없으면 생성
            phone_id = message_data.get('phoneId', '')
            phone_collection = client.collections.get("Phone")
            
            # 기존 Phone 객체 조회
            phone_response = phone_collection.query.fetch_objects(
                filters=wvc.query.Filter.by_property("phoneId").equal(phone_id),
                limit=1
            )
            
            if not phone_response.objects:
                # 🔧 RFC3339 형식으로 날짜 생성 (마이크로초 제거)
                timestamp = message_data.get('timestamp')
                if timestamp:
                    # ISO 형식에서 마이크로초 제거하고 Z 추가
                    if '.' in timestamp:
                        timestamp = timestamp.split('.')[0] + 'Z'
                    elif not timestamp.endswith('Z'):
                        timestamp = timestamp + 'Z'
                else:
                    # 현재 시간을 RFC3339 형식으로 생성
                    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                
                # Phone 객체 생성
                phone_uuid = phone_collection.data.insert({
                    "phoneId": phone_id,
                    "created_at": timestamp
                })
                logger.info(f"📞 새로운 Phone 객체 생성: {phone_id} -> {phone_uuid}")
            else:
                phone_uuid = phone_response.objects[0].uuid
                logger.info(f"📞 기존 Phone 객체 사용: {phone_id} -> {phone_uuid}")
            
            # 2. VoiceConversation 객체 저장 (reference 사용)
            conversation_collection = client.collections.get("VoiceConversation")
            conversation_collection.data.insert(
                properties={
                    "message": message_data.get('text', ''),
                    "speaker": "user"  # VoiceConversation 스키마에 맞춤
                },
                references={
                    "phoneId": phone_uuid  # Phone 객체의 UUID 참조
                }
            )
            
            logger.info(f"💾 [LLM Domain] Weaviate 저장 완료 - Session: {message_data.get('sessionId')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [LLM Domain] Weaviate 저장 실패: {e}")
            return False
    
    def create_tts_message(self, llm_response: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """TTS 서버로 전송할 메시지 생성"""
        # 🔧 RFC3339 형식으로 타임스탬프 생성
        timestamp = original_data.get('timestamp')
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        elif '.' in timestamp and not timestamp.endswith('Z'):
            # 마이크로초 제거하고 Z 추가
            timestamp = timestamp.split('.')[0] + 'Z'
        elif not timestamp.endswith('Z'):
            timestamp = timestamp + 'Z'
            
        return {
            "text": llm_response,
            "phoneId": original_data.get('phoneId', ''),
            "sessionId": original_data.get('sessionId', ''),
            "requestId": original_data.get('requestId', ''),
            "timestamp": timestamp,
            "voice_config": {
                "language": "ko",
                "speed": 1.0
            }
        }
    
    def validate_text_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 요청 데이터 유효성 검증"""
        required_fields = ['text', 'phoneId', 'sessionId', 'requestId']
        missing_fields = []
        
        for field in required_fields:
            if not request_data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            return {
                'valid': False,
                'error': f'필수 필드가 누락되었습니다: {", ".join(missing_fields)}'
            }
        
        # 텍스트 길이 검증
        text = request_data.get('text', '')
        if len(text) > 5000:
            return {
                'valid': False,
                'error': '텍스트가 너무 깁니다. (최대 5000자)'
            }
        
        return {'valid': True}

# 싱글톤 인스턴스
llm_domain_service = LLMDomainService() 