# ai/ask.py
import json
import asyncio
import os
import sys
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from dotenv import load_dotenv
import logging

# API KEY 정보로드
load_dotenv()
# 🔥 Ollama 추가 import
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from ..utils.prompts import prompt

logger = logging.getLogger(__name__)

class LangchainStreamProcessor:
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.current_question = ""
        self.is_processing = False
        self.current_task: Optional[asyncio.Task] = None
        self.cancel_event = threading.Event()
        self.is_eos_received = False
        
        # 마지막 완료된 응답 저장
        self.last_completed_response = ""
        self.last_completed_question = ""
        
        # Langchain 설정
        self.setup_langchain()
    
    def setup_langchain(self):
        """Langchain 체인 설정"""

        self.llm = ChatOllama(
            model="gpt-oss:20b",
            base_url="http://192.168.0.7:11434",  # Ollama 서버 주소
            temperature=0.3,
            # keep_alive=-1,  # 모델을 메모리에 유지
        )

        # 일반 Chain 생성
        self.chain = prompt | self.llm | StrOutputParser()

        # 세션 기록을 저장할 딕셔너리
        self.store = {}

        # 세션 기록 관리 체인
        self.chain_with_history = RunnableWithMessageHistory(
            self.chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
    
    def get_session_history(self, session_ids):
        """세션 ID를 기반으로 세션 기록을 가져오는 함수"""
        logger.info(f"[대화 세션ID]: {session_ids}")
        if session_ids not in self.store:
            self.store[session_ids] = ChatMessageHistory()
        return self.store[session_ids]

    async def process_stream_token(self, token: str) -> Dict[str, Any]:
        """스트림 토큰을 처리하는 메인 메서드 - 진정한 실시간 스트리밍"""
        
        logger.info(f"🎯 [{self.session_id}] 토큰 수신: '{token}'")
        
        if token == '<eos>':
            logger.info(f"🏁 [{self.session_id}] EOS 감지 - 질문 완료 처리")
            self.is_eos_received = True
            
            # 🔥 현재 진행 중인 작업이 있으면 즉시 중단
            if self.current_task and not self.current_task.done():
                logger.info(f"🛑 [{self.session_id}] EOS: 진행 중인 미리보기 즉시 중단")
                self.current_task.cancel()
                self.cancel_event.set()
                
                # 짧은 대기로 취소 처리
                try:
                    await asyncio.wait_for(self.current_task, timeout=0.1)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.info(f"🔄 [{self.session_id}] EOS: 미리보기 중단 완료")
            
            # 현재 질문으로 최종 답변 생성
            if self.current_question.strip():
                logger.info(f"🚀 [{self.session_id}] 최종 질문으로 답변 생성: '{self.current_question}'")
                
                # 최종 답변 생성
                result = await self.generate_final_response()
                
                # 상태 초기화
                question = self.current_question.strip()
                self.current_question = ""
                self.is_eos_received = False
                self.current_task = None
                
                return {
                    "type": "complete",
                    "content": result.get("content", ""),
                    "question": question,
                    "message": "EOS로 인한 최종 답변 완료",
                    "timestamp": datetime.now().isoformat(),
                    "processing_stats": result.get("processing_stats", {})
                }
            else:
                # 질문이 없는 경우
                logger.info(f"❓ [{self.session_id}] EOS 수신했지만 질문이 없음")
                return {
                    "type": "complete",
                    "content": "질문을 입력해주세요.",
                    "question": "",
                    "message": "빈 질문으로 EOS 수신",
                    "timestamp": datetime.now().isoformat()
                }
        
        else:
            # 🔥 기존 작업이 있으면 즉시 중단 (진정한 병렬 처리)
            if self.current_task and not self.current_task.done():
                logger.info(f"🛑 [{self.session_id}] 새 토큰으로 기존 미리보기 즉시 중단: '{token}'")
                self.current_task.cancel()
                self.cancel_event.set()
                
                # 🔥 취소 완료를 기다리지 않고 즉시 진행 (진정한 논블로킹)
                # 이전 작업은 백그라운드에서 알아서 정리됨
            
            # 질문 업데이트
            old_question = self.current_question
            self.current_question += token
            self.cancel_event.clear()  # 새 작업용 이벤트 클리어
            self.is_eos_received = False

            logger.info(f"📊 [{self.session_id}] 질문 업데이트: '{old_question}' → '{self.current_question}'")
            
            # 실시간 미리보기 생성 (빠른 응답)
            if len(self.current_question.strip()) > 3:  # 최소 3자 이상일 때만
                logger.info(f"👁️ [{self.session_id}] 실시간 미리보기 생성 시작...")
                preview_result = await self.generate_preview_response()
                
                return {
                    "type": "preview",  # 미리보기임을 명시
                    "content": preview_result.get("content", ""),
                    "current_question": self.current_question,
                    "message": "실시간 미리보기",
                    "timestamp": datetime.now().isoformat(),
                    "processing_stats": preview_result.get("processing_stats", {})
                }
            else:
                # 질문이 너무 짧으면 단순 확인만
                return {
                    "type": "typing",
                    "current_question": self.current_question,
                    "message": "입력 중...",
                    "timestamp": datetime.now().isoformat()
                }

    async def generate_preview_response(self) -> Dict[str, Any]:
        """빠른 미리보기 응답 생성 - 진정한 논블로킹"""
        try:
            start_time = time.time()
            
            # 🔥 새로운 미리보기 태스크를 즉시 시작 (이전 작업 기다리지 않음)
            # 이전 작업의 취소는 process_stream_token에서 이미 처리됨
            
            logger.info(f"🚀 [{self.session_id}] 새 미리보기 태스크 즉시 시작")
            
            # 새 미리보기 태스크 생성 및 시작
            self.current_task = asyncio.create_task(self._generate_preview())
            result = await self.current_task
            
            elapsed_time = time.time() - start_time
            logger.info(f"👁️ [{self.session_id}] 미리보기 생성 완료: {elapsed_time:.2f}초")
            
            return result
            
        except asyncio.CancelledError:
            elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.info(f"🔄 [{self.session_id}] 미리보기 중단됨 ({elapsed_time:.2f}초) - 새 토큰으로 인한 중단")
            return {
                "content": "중단됨...",
                "processing_stats": {"status": "cancelled", "elapsed_time": elapsed_time}
            }
        except Exception as e:
            logger.error(f"❌ [{self.session_id}] 미리보기 생성 오류: {e}")
            return {
                "content": "처리 중...",
                "processing_stats": {"error": str(e)}
            }

    async def _generate_preview(self) -> Dict[str, Any]:
        """실제 미리보기 생성 로직 - 강화된 중단 감지"""
        try:
            content = ""
            chunk_count = 0
            start_time = time.time()
            
            # 🔥 더 빠른 미리보기 - 2개 청크만
            max_chunks = 2  # 더 빠른 응답을 위해 2개로 줄임
            
            logger.info(f"🚀 [{self.session_id}] 미리보기 스트림 시작: '{self.current_question}'")
            
            # 🔥 스트림 생성 전 최종 취소 확인
            if self.cancel_event.is_set():
                logger.info(f"⚠️ [{self.session_id}] 스트림 시작 전 취소 감지됨")
                raise asyncio.CancelledError("시작 전 취소됨")
            
            # 🔥 스트림을 더 작은 단위로 처리
            stream_iter = self.chain_with_history.stream(
                {"input": self.current_question},
                config={"configurable": {"session_id": self.session_id}}
            )
            
            for chunk in stream_iter:
                # 🔥 매 반복마다 즉시 취소 확인
                if self.cancel_event.is_set():
                    logger.info(f"⚠️ [{self.session_id}] 미리보기 중단! (청크 {chunk_count}) - 새 토큰으로 인한 취소")
                    raise asyncio.CancelledError(f"청크 {chunk_count}에서 새 토큰으로 인해 취소됨")
                
                if chunk:
                    chunk_count += 1
                    content += str(chunk)
                    
                    # 🔥 청크 추가 직후에도 취소 확인
                    if self.cancel_event.is_set():
                        logger.info(f"⚠️ [{self.session_id}] 청크 추가 후 취소 감지 (청크 {chunk_count})")
                        raise asyncio.CancelledError(f"청크 {chunk_count} 추가 후 취소됨")
                    
                    # 미리보기 청크 제한
                    if chunk_count >= max_chunks:
                        content += "..."
                        logger.info(f"📏 [{self.session_id}] 미리보기 청크 제한 도달 ({max_chunks}개)")
                        break
                
                # 🔥 각 청크 사이에 잠깐 yield (다른 작업이 실행될 기회 제공)
                await asyncio.sleep(0)  # 제어권을 이벤트 루프에 양보
            
            elapsed_time = time.time() - start_time
            
            return {
                "content": content.strip() or "생각 중...",
                "processing_stats": {
                    "chunk_count": chunk_count,
                    "elapsed_time": round(elapsed_time, 2),
                    "content_length": len(content),
                    "type": "preview"
                }
            }
            
        except asyncio.CancelledError as e:
            elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.info(f"🔄 [{self.session_id}] 미리보기 취소됨: {str(e)} ({elapsed_time:.2f}초 후, 청크: {chunk_count if 'chunk_count' in locals() else 0})")
            raise  # 🔥 CancelledError를 다시 raise
            
        except Exception as e:
            logger.error(f"❌ [{self.session_id}] 미리보기 생성 실패: {e}")
            return {
                "content": "처리 중...",
                "processing_stats": {"error": str(e)}
            }

    async def generate_final_response(self) -> Dict[str, Any]:
        """EOS 수신 시 최종 완전한 답변 생성"""
        try:
            start_time = time.time()
            content = ""
            chunk_count = 0
            
            logger.info(f"🎯 [{self.session_id}] 최종 답변 생성 시작: '{self.current_question}'")
            
            # 완전한 답변 생성 (제한 없음)
            for chunk in self.chain_with_history.stream(
                {"input": self.current_question},
                config={"configurable": {"session_id": self.session_id}}
            ):
                if chunk:
                    chunk_count += 1
                    content += str(chunk)
            
            elapsed_time = time.time() - start_time
            
            # 완료된 응답 저장
            if content.strip():
                self.last_completed_response = content.strip()
                self.last_completed_question = self.current_question
                logger.info(f"💾 [{self.session_id}] 최종 응답 저장됨")
            
            logger.info(f"✅ [{self.session_id}] 최종 답변 완료! 총 {chunk_count}개 청크, {elapsed_time:.2f}초 소요")
            logger.info(f"📄 [{self.session_id}] 최종 응답 길이: {len(content)}자")
            
            return {
                "content": content.strip(),
                "processing_stats": {
                    "chunk_count": chunk_count,
                    "elapsed_time": round(elapsed_time, 2),
                    "content_length": len(content),
                    "type": "final"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [{self.session_id}] 최종 답변 생성 실패: {e}")
            return {
                "content": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "processing_stats": {"error": str(e)}
            }

    def reset(self):
        """현재 상태 초기화"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        self.current_question = ""
        self.current_task = None
        self.cancel_event.clear()
        self.is_eos_received = False
        # 마지막 완료된 응답은 유지 (세션이 계속될 수 있으므로)
        # self.last_completed_response = ""
        # self.last_completed_question = ""
        logger.info("프로세서가 초기화되었습니다.")


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
       
        await self.accept()
        
        # 클라이언트 고유 ID 생성 (channel_name 대신 현재 시간과 객체 ID 사용)
        self.phone_Id = phone_Id
        self.session_id = session_Id
        self.is_connected = True  # 연결 상태 추가
      
        # 프로세서 생성
        processor = LangchainStreamProcessor(session_id=self.session_id)
        ChatConsumer.processors[self.phone_Id] = processor
        
        logger.info(f"새 클라이언트 연결: {self.phone_Id} (세션: {self.session_id})")
        
        # 연결 확인 메시지 전송
        await self.safe_send({
            "type": "connection_established",
            "phone_Id": self.phone_Id,
            "session_id": self.session_id,
            "message": "WebSocket 연결이 성공적으로 설정되었습니다.",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"[{self.phone_Id}] 연결 초기화 완료")

    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        logger.info(f"클라이언트 {self.phone_Id} 연결 종료 (코드: {close_code})")
        self.is_connected = False  # 연결 상태 변경
        await self.cleanup_client()

    def is_websocket_connected(self) -> bool:
        """WebSocket 연결 상태 확인"""
        # 기본적으로 is_connected 플래그만 확인
        if not hasattr(self, 'is_connected'):
            return True  # 초기 상태에서는 연결된 것으로 간주
        return self.is_connected

    async def safe_send(self, data: dict):
        """안전한 메시지 전송 (연결 상태 확인)"""
        if not self.is_websocket_connected():
            logger.warning(f"[{getattr(self, 'phone_Id', 'unknown')}] WebSocket 연결이 종료되어 메시지를 전송하지 않습니다.")
            return False
            
        try:
            await self.send(text_data=json.dumps(data, ensure_ascii=False))
            logger.debug(f"[{getattr(self, 'phone_Id', 'unknown')}] 메시지 전송 성공")
            return True
        except Exception as e:
            # ClientDisconnected, ConnectionClosedOK 등의 연결 종료 예외 확인
            if 'ClientDisconnected' in str(type(e)) or 'ConnectionClosed' in str(type(e)):
                logger.warning(f"[{getattr(self, 'phone_Id', 'unknown')}] WebSocket 연결이 종료됨: {e}")
                self.is_connected = False  # 연결 종료 시 상태 변경
            else:
                logger.error(f"[{getattr(self, 'phone_Id', 'unknown')}] 메시지 전송 실패: {e}")
            return False

    async def receive(self, text_data):
        """메시지 수신 처리 - 즉시 반환으로 논블로킹"""
        logger.info(f"[{self.phone_Id}] 원본 메시지 수신: {repr(text_data)}")
        
        try:
            # JSON 메시지 파싱
            data = json.loads(text_data)
            logger.info(f"[{self.phone_Id}] JSON 파싱 성공: {data}")
            
            # 🔥 즉시 처리 후 바로 반환 (블로킹 없음)
            await self.handle_json_message(data)
            # receive 메서드가 즉시 완료되어 다음 메시지를 받을 수 있음
            
        except Exception as e:
            logger.error(f"[{self.phone_Id}] 메시지 처리 중 오류: {e}")
            # 🔥 오류 응답도 논블로킹으로 처리
            asyncio.create_task(self.send_error_response(str(e)))

    async def handle_json_message(self, data: dict):
        """JSON 형식 메시지 처리 - 완전 논블로킹"""
        if data.get("token"): 
            # 토큰 처리
            token = data.get("token", "")
            request_Id = data.get("request_id", "")
            logger.info(f"[{self.phone_Id}] 토큰 처리: '{token}' , request_Id 처리: '{request_Id}'")
            
            # 🔥 즉시 반환 - WebSocket이 다음 메시지를 받을 수 있도록
            # asyncio.create_task를 사용하여 완전히 분리된 태스크로 실행
            task = asyncio.create_task(self.process_token_and_respond(token, request_Id))
            
            # 🔥 태스크를 fire-and-forget으로 실행 (await 없음)
            # WebSocket 메시지 처리가 즉시 완료되어 다음 메시지를 받을 수 있음
            logger.info(f"[{self.phone_Id}] 토큰 '{token}' 처리 태스크 시작됨 (논블로킹)")
        
    async def process_token_and_respond(self, token: str, request_Id: str):
        """토큰을 처리하고 응답을 전송 - 진정한 병렬 처리"""
        if not self.is_websocket_connected():
            logger.warning(f"[{self.phone_Id}] 연결이 끊어져 토큰 처리를 중단합니다: '{token}'")
            return
            
        processor = ChatConsumer.processors.get(self.phone_Id)
        if not processor:
            logger.error(f"[{self.phone_Id}] 프로세서를 찾을 수 없습니다.")
            await self.send_error_response("프로세서를 찾을 수 없습니다.")
            return
        
        start_time = time.time()
        logger.info(f"🎮 [{self.phone_Id}] 토큰 처리 시작: '{token}' (병렬)")
        
        try:
            # 🔥 토큰 처리를 병렬로 즉시 시작 (블로킹 없음)
            result = await processor.process_stream_token(token)
            processing_time = time.time() - start_time
            
            # 🔥 취소된 작업인지 확인
            if result.get("processing_stats", {}).get("status") == "cancelled":
                logger.info(f"🔄 [{self.phone_Id}] 취소된 작업 결과 무시: '{token}'")
                return
            
            # 결과를 클라이언트에게 전송
            response = {
                "phone_Id": self.phone_Id,
                "token_received": token,
                "processing_time": round(processing_time, 3),
                **result
            }
            
            # 안전한 전송
            success = await self.safe_send(response)
            if not success:
                logger.warning(f"[{self.phone_Id}] 응답 전송 실패, 하지만 처리는 계속 진행")
            
            # 완료된 답변만 TTS로 전송
            if result["type"] == "complete":
                tts_message = {
                    'phoneId': self.phone_Id,
                    'sessionId': self.session_id,
                    'requestId': request_Id,
                    'voice_config': {'language': 'ko'},
                    'text': result['content']
                }

                stats = result.get("processing_stats", {})
                logger.info(f"🎉 [{self.phone_Id}] 최종 답변 완료!")
                logger.info(f"📝 질문: '{result.get('question', '')}'")
                logger.info(f"📄 답변 길이: {len(result.get('content', ''))}자")
                logger.info(f"⏱️ 총 처리 시간: {processing_time:.3f}초")

                # TTS 서버로 전송
                send_result = self.send_to_tts_server(tts_message)

                return {
                    'status': stats,
                    'llm_response': result['content'][:100],
                    'tts_response': send_result,
                    'processing_time': processing_time,
                }
            
            elif result["type"] == "preview":
                logger.info(f"👁️ [{self.phone_Id}] 실시간 미리보기 전송 (병렬)")
                logger.info(f"⏱️ 미리보기 처리 시간: {processing_time:.3f}초")
                
            elif result["type"] == "typing":
                logger.info(f"⌨️ [{self.phone_Id}] 입력 상태 전송")
                
        except asyncio.CancelledError:
            processing_time = time.time() - start_time
            logger.info(f"🔄 [{self.phone_Id}] 토큰 처리 취소됨: '{token}' ({processing_time:.3f}초)")
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"💥 [{self.phone_Id}] 토큰 처리 중 예외 발생: {e}")
            logger.info(f"⏱️ 예외 발생까지 시간: {processing_time:.3f}초")
            
            if self.is_websocket_connected():
                await self.send_error_response(str(e))

    async def send_error_response(self, error_message: str):
        """오류 응답 전송 (연결 상태 확인)"""
        if not self.is_websocket_connected():
            logger.warning(f"[{getattr(self, 'phone_Id', 'unknown')}] 연결이 끊어져 오류 응답을 전송하지 않습니다.")
            return
            
        await self.safe_send({
            "type": "error",
            "error": error_message,
            "phone_Id": self.phone_Id,
            "timestamp": datetime.now().isoformat()
        })

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

    def send_to_tts_server(self, tts_message: Dict[str, Any]) -> Dict[str, Any]:
        self.tts_server_url = getattr(settings, 'TTS_SERVER_URL', 'http://tts_server:5002')
        """TTS 서버로 HTTP POST 전송"""
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
                
                response = requests.post(
                    tts_url, 
                    json=tts_message, 
                    headers=headers,
                    timeout=30, 
                    verify=False
                )
                
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