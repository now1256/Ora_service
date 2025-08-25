# ai/chat_consumer.py
import json
import asyncio
import os
import sys
import time
from typing import Dict, Any
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

# stream_processor에서 필요한 것들 import
from .stream_processor import (
    LangchainStreamProcessor,
    get_or_create_json_manager,
    get_or_create_user_system,
    _json_managers_cache
)

logger = logging.getLogger(__name__)

# 공통 HTTP 클라이언트 import 시도
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
try:
    from shared.infrastructure.http_client import http_client
except ImportError:
    # 공통 클라이언트를 찾을 수 없는 경우 requests 직접 사용
    import requests
    http_client = None

class ChatConsumer(AsyncWebsocketConsumer):
    """Django Channels WebSocket Consumer for Chat"""
    
    # 클래스 레벨에서 모든 클라이언트의 프로세서 관리
    processors = {}
    
    async def connect(self):
        """WebSocket 연결 수락"""
      
        headers = dict(self.scope['headers'])
        phone_Id = headers.get(b'phone-id', b'').decode()
        session_Id = headers.get(b'session-id', b'').decode()
       
        if not phone_Id or not session_Id :
            return JsonResponse({'success': False, 'message': 'header값 누락'}, status=400)
            
        get_or_create_json_manager(phone_Id)
        get_or_create_user_system(phone_Id)

        # 클라이언트 고유 ID 생성 (channel_name 대신 현재 시간과 객체 ID 사용)
        self.phone_Id = phone_Id
        self.session_id = session_Id
     
        
        # 프로세서 생성
        processor = LangchainStreamProcessor(session_id=self.session_id, phone_id=self.phone_Id)
        ChatConsumer.processors[self.phone_Id] = processor
        
        logger.info(f"새 클라이언트 연결: {self.phone_Id} (세션: {self.session_id})")
        await self.accept()
        # 연결 확인 메시지 전송
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "phone_Id": self.phone_Id,
            "session_id": self.session_id,
            "message": "WebSocket 연결이 성공적으로 설정되었습니다.",
            "timestamp": datetime.now().isoformat()
        }))
        
        logger.info(f"[{self.phone_Id}] 연결 초기화 완료")

    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        logger.info(f"클라이언트 {self.phone_Id} 연결 종료 (코드: {close_code})")
        try:
            from .stream_processor import get_or_create_rag_manager
            rag_manager = get_or_create_rag_manager()
            logger.info(f"🔄 [{self.phone_Id}] 벡터스토어 업데이트 시작...")
            rag_manager.refresh_user_vectorstore(self.phone_Id)
            logger.info(f"✅ [{self.phone_Id}] 벡터스토어 업데이트 완료")
        except Exception as e:
            logger.error(f"❌ [{self.phone_Id}] disconnect 처리 중 전체 오류: {e}")
                
        # 클라이언트 정리
        await self.cleanup_client()

    async def receive(self, text_data):
        """메시지 수신 처리"""
        logger.info(f"[{self.phone_Id}] 원본 메시지 수신: {repr(text_data)}")
        
        try:
            # JSON 메시지 파싱
            data = json.loads(text_data)
            logger.info(f"[{self.phone_Id}] JSON 파싱 성공: {data}")
            await self.handle_json_message(data)
            
        except Exception as e:
            logger.error(f"[{self.phone_Id}] 메시지 처리 중 오류: {e}")
            await self.send_error_response(str(e))

    async def handle_json_message(self, data: dict):
        """JSON 형식 메시지 처리"""
        if data.get("token"):
            # 토큰 처리
            token = data.get("token", "")
            request_id = data.get("request_id", "")
            logger.info(f"[{self.phone_Id}] 토큰 처리: '{token}'")
            
            # 비동기로 토큰 처리
            asyncio.create_task(
                self.process_token_and_respond(token,request_id)
            )

    async def process_token_and_respond(self, token: str, request_id: str):
        """토큰을 처리하고 응답을 전송"""
        processor = ChatConsumer.processors.get(self.phone_Id)
        if not processor:
            logger.error(f"[{self.phone_Id}] 프로세서를 찾을 수 없습니다.")
            await self.send_error_response("프로세서를 찾을 수 없습니다.")
            return
                
        start_time = time.time()
                
        try:
            result = await processor.process_stream_token(token)
            processing_time = time.time() - start_time
                        
            # 결과를 클라이언트에게 전송
            response = {
                "phone_Id": self.phone_Id,
                "token_received": token,
                "processing_time": round(processing_time, 3),
                **result
            }
                        
            await self.send(text_data=json.dumps(response, ensure_ascii=False))
                        
            # 상세 로그 출력
            if result["type"] == "complete":
                json_manager = _json_managers_cache.get(self.phone_Id)
                
                # EOS로 완료된 경우에만 완성된 대화로 저장
                question = result.get('question', '').strip()
                content = result.get('content', '').strip()
                                
                if question and content:
                    # 프로세서에 완성된 대화 저장 (disconnect에서 사용)
                    processor.save_completed_conversation(question, content)
                    logger.info(f"✅ [{self.phone_Id}] 완성된 대화 프로세서에 저장됨")
                                
                    tts_message = {
                        'phoneId': self.phone_Id,
                        'sessionId': self.session_id,
                        'requestId': request_id,
                        'voice_config': {'language': 'ko'},
                        'text': content
                    }
                                
                    stats = result.get("processing_stats", {})
                    logger.info(f"🎉 [{self.phone_Id}] 최종 답변 완료!")
                    logger.info(f"📝 질문: '{question}'")
                    logger.info(f"📄 답변 길이: {len(content)}자")
                    logger.info(f"⏱️ 총 처리 시간: {processing_time:.3f}초")
                    
                    # TTS 서버로 비동기 전송 (백그라운드에서 실행)

                    ora_message = {
                        'text': content,
                        'sessionId': self.session_id,
                        'requestId': request_id,
                        'phoneId': self.phone_Id,
                    }
                 
                    ora_task = asyncio.create_task(self.send_to_external_server(
                        ora_message
                    ))
                    # tts_task = asyncio.create_task(self.send_to_tts_server(tts_message))
                    
                    asyncio.create_task(asyncio.to_thread(json_manager.add_conversation, question, content))



                    return {
                        'status': stats,
                        'llm_response': content[:100],
                        'tts_task': ora_task,  # 필요시 나중에 await 가능
                        'processing_time': processing_time,
                    }
                    
                    # 즉시 return (TTS 전송 완료를 기다리지 않음)
                    # return {
                    #     'status': stats,
                    #     'llm_response': content[:100],
                    #     'tts_task': tts_task,  # 필요시 나중에 await 가능
                    #     'processing_time': processing_time,
                    # }
                
                    
            elif result["type"] == "interrupted":
                logger.info(f"⚡ [{self.phone_Id}] 실시간 답변 진행 중... (저장하지 않음)")
                logger.info(f"⏱️ 현재까지 처리 시간: {processing_time:.3f}초")
                
            elif result["type"] == "error":
                logger.error(f"❌ [{self.phone_Id}] 처리 오류: {result.get('error', '')}")
                logger.info(f"⏱️ 오류 발생까지 시간: {processing_time:.3f}초")
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"💥 [{self.phone_Id}] 토큰 처리 중 예외 발생: {e}")
            logger.info(f"⏱️ 예외 발생까지 시간: {processing_time:.3f}초")
            await self.send_error_response(str(e))

    async def send_error_response(self, error_message: str):
        """오류 응답 전송"""
        await self.send(text_data=json.dumps({
            "type": "error",
            "error": error_message,
            "phone_Id": self.phone_Id,
            "timestamp": datetime.now().isoformat()
        }))

    async def cleanup_client(self):
        """클라이언트 연결 정리"""
        if hasattr(self, 'phone_Id') and self.phone_Id in ChatConsumer.processors:
            processor = ChatConsumer.processors[self.phone_Id]
            processor.reset()  # 진행 중인 작업 정리
            del ChatConsumer.processors[self.phone_Id]
            logger.info(f"클라이언트 {self.phone_Id} 정리 완료")

    async def send_to_external_server(self, tts_message: Dict[str, Any]) -> Dict[str, Any]:
        """TTS 서버로 HTTP POST 전송"""
        self.tts_server_url = getattr(settings, 'TTS_SERVER_URL', 'http://100.72.196.9:8080')
        logger.info(tts_message)
        try:
            tts_url = f"{self.tts_server_url}/api/tts/naver/test"
            
            # 전송할 데이터 로깅
            logger.info(f"📤 [LLM Workflow] TTS 서버로 HTTP 전송: {tts_url}")
            logger.info(f"📦 [LLM Workflow] 전송 데이터: {tts_message}")

            if http_client:
                response = http_client.post(tts_url, tts_message)
                return response
            else:
                import requests
                
                # 헤더를 명시적으로 설정
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                start_time = time.time()
                response = requests.post(
                    tts_url, 
                    json=tts_message, 
                    headers=headers,
                    timeout=30, 
                    verify=False
                )
                end_time = time.time() - start_time
                logger.info(f"오라 서버까지 가는데 걸리는 시간 {end_time}")
                logger.info(f"📡 [LLM Workflow] 응답 상태코드: {response.status_code}")
                logger.info(f"📄 [LLM Workflow] 응답 내용: {response.text[:500]}")

                if response.status_code == 200:
                    logger.info("✅ [LLM Workflow] TTS 서버로 전송 성공!")
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'data': response.json() if response.content else None
                    }
                else:
                    logger.error(f"❌ [LLM Workflow] TTS 서버 전송 실패: {response.status_code}")
                    logger.error(f"📄 [LLM Workflow] 오류 응답: {response.text}")
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

    async def send_to_tts_server(self, tts_message: Dict[str, Any]) -> Dict[str, Any]:
        """TTS 서버로 HTTP POST 전송"""
        self.tts_server_url = getattr(settings, 'TTS_SERVER_URL', 'http://tts_server:5002')
        
        try:
            tts_url = f"{self.tts_server_url}/api/convert-tts/"
            
            # 전송할 데이터 로깅
            logger.info(f"📤 [LLM Workflow] TTS 서버로 HTTP 전송: {tts_url}")
            logger.info(f"📦 [LLM Workflow] 전송 데이터: {tts_message}")

            if http_client:
                response = http_client.post(tts_url, tts_message)
                return response
            else:
                import requests
                
                # 헤더를 명시적으로 설정
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                start_time = time.time()
                response = requests.post(
                    tts_url, 
                    json=tts_message, 
                    headers=headers,
                    timeout=30, 
                    verify=False
                )
                end_time = time.time() - start_time
                logger.info(f"tts까지 가는데 걸리는 시간 {end_time}")
                logger.info(f"📡 [LLM Workflow] 응답 상태코드: {response.status_code}")
                logger.info(f"📄 [LLM Workflow] 응답 내용: {response.text[:500]}")

                if response.status_code == 200:
                    logger.info("✅ [LLM Workflow] TTS 서버로 전송 성공!")
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'data': response.json() if response.content else None
                    }
                else:
                    logger.error(f"❌ [LLM Workflow] TTS 서버 전송 실패: {response.status_code}")
                    logger.error(f"📄 [LLM Workflow] 오류 응답: {response.text}")
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