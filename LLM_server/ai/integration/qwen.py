# ai/consumers.py
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
import torch
from ..utils.prompts import prompt
from ..models.qwen_model import qwen_model

logger = logging.getLogger(__name__)


# API KEY 정보로드
load_dotenv()


class QwenStreamProcessor:
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

        # 대화 히스토리 관리 (간단한 메모리 저장)
        self.conversation_history = []
        
        # 모델 정보
        self.model_name = "Qwen/Qwen2.5-7B-Instruct"
        
   

    async def process_stream_token(self, token: str) -> Dict[str, Any]:
        """스트림 토큰을 처리하는 메인 메서드"""

        logger.info(f"🎯 [{self.session_id}] 토큰 수신: '{token}'")

        if token == '<eos>':
            logger.info(f"🏁 [{self.session_id}] EOS 감지 - 현재 진행중인 답변을 끝까지 완료합니다.")
            self.is_eos_received = True

            if self.current_task and not self.current_task.done():
                logger.info(f"⏳ [{self.session_id}] 진행 중인 태스크 대기 중...")
                try:
                    result = await self.current_task
                    question = self.current_question.strip()

                    logger.info(f"🎉 [{self.session_id}] EOS 처리 완료! 질문: '{question}'")

                    # 대화 히스토리에 추가
                    if question and result.get("content"):
                        self.conversation_history.append({
                            "role": "user",
                            "content": question
                        })
                        self.conversation_history.append({
                            "role": "assistant", 
                            "content": result.get("content")
                        })
                        
                        # 히스토리 길이 제한 (최근 10개 대화만 유지)
                        if len(self.conversation_history) > 20:
                            self.conversation_history = self.conversation_history[-20:]

                    # EOS 처리 완료 후 상태 초기화 (TTS 전송 전에)
                    self.current_question = ""
                    self.is_eos_received = False
                    self.current_task = None

                    return {
                        "type": "complete",
                        "content": result.get("content", ""),
                        "question": question,
                        "message": "EOS로 인한 완전한 답변 완료",  # 🔥 TTS 전송 구분용 메시지
                        "timestamp": datetime.now().isoformat(),
                        "processing_stats": result.get("processing_stats", {}),
                        "model_used": f"Qwen {self.model_name}",
                        "tts_required": True  # 🔥 TTS 전송 필요 플래그
                    }
                except Exception as e:
                    logger.error(f"❌ [{self.session_id}] EOS 처리 중 오류: {e}")
                    return {
                        "type": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "model_used": f"Qwen {self.model_name}"
                    }
            else:
                # 진행 중인 태스크가 없는 경우 - 마지막 완료된 응답 반환
                if self.last_completed_response:
                    logger.info(f"📝 [{self.session_id}] 진행 중인 태스크 없음, 마지막 완료된 응답 반환")

                    # 마지막 완료된 응답 반환 후 current_question 초기화
                    question = self.last_completed_question
                    self.current_question = ""
                    self.is_eos_received = False

                    return {
                        "type": "complete",
                        "content": self.last_completed_response,
                        "question": question,
                        "message": "마지막 완료된 응답 반환",
                        "timestamp": datetime.now().isoformat(),
                        "model_used": f"Qwen {self.model_name}",
                        "tts_required": False  # 🔥 TTS 전송 불필요
                    }
                else:
                    logger.info(f"❓ [{self.session_id}] 완료된 응답이 없어서 빈 응답 처리")

                    # 빈 응답 처리 시에도 current_question 초기화
                    question = self.current_question.strip()
                    self.current_question = ""
                    self.is_eos_received = False

                    return {
                        "type": "complete",
                        "content": "질문이 완료되었습니다.",
                        "question": question,
                        "message": "완료된 응답 없이 EOS 수신",
                        "timestamp": datetime.now().isoformat(),
                        "model_used": f"Qwen {self.model_name}",
                        "tts_required": False  # 🔥 TTS 전송 불필요
                    }
        else:
            # 현재 진행 중인 응답이 있으면 중단
            if self.current_task and not self.current_task.done():
                logger.info(f"🛑 [{self.session_id}] 이전 태스크 중단 시작...")
                self.current_task.cancel()
                self.cancel_event.set()

                try:
                    await self.current_task
                    logger.info(f"✅ [{self.session_id}] 이전 태스크 중단 완료")
                except asyncio.CancelledError:
                    logger.info(f"🔄 [{self.session_id}] 이전 태스크 취소됨")

            # 토큰을 현재 질문에 추가
            old_question = self.current_question
            self.current_question += token
            self.cancel_event.clear()
            self.is_eos_received = False

            logger.info(f"📊 [{self.session_id}] 질문 업데이트: '{old_question}' → '{self.current_question}'")
            logger.info(f"🔄 [{self.session_id}] 새로운 Qwen 실시간 답변 생성 시작...")

            return await self.generate_interruptible_response()

    async def generate_interruptible_response(self) -> Dict[str, Any]:
        """중단 가능한 완전한 답변 생성 - Qwen 사용 (토큰 디코딩 오류 수정)"""

        async def _generate():
            try:
                full_content = ""
                chunk_count = 0
                start_time = time.time()

                logger.info(f"🚀 [{self.session_id}] Qwen 실시간 답변 생성 시작: '{self.current_question}'")

                # Qwen 모델 상태 확인
                if qwen_model is None or not qwen_model.is_ready:
                    raise Exception("Qwen 모델이 초기화되지 않았습니다")

                # Qwen 시스템 프롬프트
                system_prompt = """당신은 실시간 한국어로만 전용 AI 복지사 오라입니다.

핵심 원칙: "빠르고 정확하게"

중요한 응답 규칙:
0. 신속하고 정확하게 20단어 이하로 답변해주세요 1초 이내로 답변을 해주도록 노력해주세요
1. 절대로 한자를 사용하지 마세요. 
2. 절대로 영어를 사용하지 마세요.
3. 오직 한글과 숫자, 기본 문장부호(.,?!) 만 사용하세요
4. 한자나 영어가 떠오르면 반드시 순수 한글로 바꿔서 말하세요
6. 이모지, 이모티콘 사용 금지
7. 친근하고 자연스럽게 말해
8. "세션", "코드", "에러" 같은 단어 사용 금지

응답 전에 한 번 더 체크하세요: 한자나 영어가 있으면 모두 한글로 바꾸세요."""

                # 대화 히스토리와 현재 질문 결합
                messages = []
                
                # 시스템 프롬프트 추가
                messages.append({"role": "system", "content": system_prompt})
                
                # 최근 대화 히스토리 추가 (최대 4개 대화)
                recent_history = self.conversation_history[-8:] if len(self.conversation_history) > 8 else self.conversation_history
                messages.extend(recent_history)
                
                # 현재 질문 추가
                messages.append({"role": "user", "content": self.current_question})

                def run_qwen_stream():
                    try:
                        logger.info(f"📡 [{self.session_id}] Qwen 모델 스트림 호출 중...")
                        logger.info(f"🤖 [{self.session_id}] 사용 모델: {self.model_name}")

                        # Qwen 모델로 스트리밍 생성
                        model = qwen_model.model
                        tokenizer = qwen_model.tokenizer

                        # 채팅 템플릿 적용
                        text = tokenizer.apply_chat_template(
                            messages,
                            tokenize=False,
                            add_generation_prompt=True
                        )

                        # 토크나이징
                        inputs = tokenizer(text, return_tensors="pt").to(model.device)

                        # 스트리밍 생성 - 수정된 버전
                        with torch.no_grad():
                            for i in range(50):  # 최대 50개 토큰 생성
                                if self.cancel_event.is_set() and not self.is_eos_received:
                                    logger.warning(f"⚠️ [{self.session_id}] 중단 이벤트 감지 - Qwen 스트림 종료")
                                    break

                                # 다음 토큰 생성
                                outputs = model.generate(
                                    inputs.input_ids,
                                    max_new_tokens=1,
                                    do_sample=True,
                                    temperature=0.3,
                                    top_p=0.8,
                                    use_cache=True,
                                    pad_token_id=tokenizer.eos_token_id,
                                    eos_token_id=tokenizer.eos_token_id
                                )

                                # 새로 생성된 토큰 ID 추출
                                new_token_ids = outputs[0][inputs.input_ids.shape[1]:]
                                if len(new_token_ids) == 0:
                                    logger.debug(f"[{self.session_id}] 새로운 토큰이 생성되지 않음")
                                    break

                                # 토큰 ID를 텍스트로 디코딩 - 오류 수정 부분
                                try:
                                    new_token = tokenizer.decode(new_token_ids, skip_special_tokens=True)
                                    
                                    # 빈 토큰이거나 공백만 있는 경우 처리
                                    if not new_token or new_token.isspace():
                                        logger.debug(f"[{self.session_id}] 빈 토큰 또는 공백 토큰 스킵")
                                        continue
                                    
                                    # 토큰이 문자열인지 확인
                                    if not isinstance(new_token, str):
                                        logger.warning(f"[{self.session_id}] 토큰이 문자열이 아님: {type(new_token)} - {new_token}")
                                        new_token = str(new_token)  # 강제로 문자열 변환
                                    
                                    logger.debug(f"[{self.session_id}] 생성된 토큰: '{new_token}' (타입: {type(new_token)})")
                                    
                                except Exception as decode_error:
                                    logger.error(f"[{self.session_id}] 토큰 디코딩 오류: {decode_error}")
                                    logger.error(f"[{self.session_id}] 문제 토큰 ID: {new_token_ids}")
                                    continue

                                # EOS 토큰 체크
                                if len(new_token_ids) > 0 and new_token_ids[-1].item() == tokenizer.eos_token_id:
                                    logger.info(f"[{self.session_id}] EOS 토큰 감지, 생성 중단")
                                    break

                                # 다음 생성을 위해 입력 업데이트
                                inputs.input_ids = outputs[0:1]
                                
                                # 성공적으로 디코딩된 토큰 반환
                                yield new_token

                                # 완료 조건 체크 (단어 수 기준)
                                current_words = new_token.split() if new_token else []
                                if len(current_words) >= 20:  # 20단어 제한
                                    logger.info(f"[{self.session_id}] 20단어 제한 도달, 생성 중단")
                                    break

                    except Exception as e:
                        logger.error(f"❌ [{self.session_id}] Qwen 스트림 오류: {e}")
                        logger.error(f"❌ [{self.session_id}] 오류 상세: {type(e).__name__}")
                        import traceback
                        logger.error(f"❌ [{self.session_id}] 스택 트레이스: {traceback.format_exc()}")
                        yield ""

                # 스트림에서 토큰들을 수집
                for chunk in run_qwen_stream():
                    if not self.is_eos_received:
                        if self.cancel_event.is_set():
                            logger.warning(f"🛑 [{self.session_id}] 새로운 토큰으로 인한 중단 요청")
                            raise asyncio.CancelledError("새로운 토큰으로 인해 중단됨")

                    if chunk and isinstance(chunk, str):  # 문자열인지 다시 한번 확인
                        chunk_count += 1
                        try:
                            full_content += chunk
                            logger.debug(f"[{self.session_id}] 청크 {chunk_count} 추가: '{chunk}' (누적: {len(full_content)}자)")
                        except Exception as concat_error:
                            logger.error(f"❌ [{self.session_id}] 문자열 연결 오류: {concat_error}")
                            logger.error(f"❌ [{self.session_id}] full_content 타입: {type(full_content)}, chunk 타입: {type(chunk)}")
                            continue
                        
                        # Qwen 스트림 진행상황 로깅
                        if chunk_count % 5 == 0:
                            logger.debug(f"🔄 [{self.session_id}] Qwen 청크 {chunk_count}개 처리됨")

                    # 비동기 처리를 위한 짧은 대기
                    await asyncio.sleep(0.01)

                elapsed_time = time.time() - start_time
                logger.info(f"✅ [{self.session_id}] Qwen 스트림 완료! 총 {chunk_count}개 청크, {elapsed_time:.2f}초 소요")
                logger.info(f"📄 [{self.session_id}] 최종 응답 길이: {len(full_content)}자")
                logger.info(f"🎯 [{self.session_id}] 응답 미리보기: '{full_content[:100]}{'...' if len(full_content) > 100 else ''}'")
                if elapsed_time > 0:
                    logger.info(f"⚡ [{self.session_id}] Qwen 평균 속도: {chunk_count/elapsed_time:.1f} 청크/초")

                # 완료된 응답을 저장
                if full_content.strip():
                    self.last_completed_response = full_content.strip()
                    self.last_completed_question = self.current_question
                    logger.info(f"💾 [{self.session_id}] Qwen 완료된 응답 저장됨")

                return {
                    "type": "interrupted" if not self.is_eos_received else "complete",
                    "content": full_content.strip(),
                    "current_question": self.current_question,
                    "timestamp": datetime.now().isoformat(),
                    "model_used": f"Qwen {self.model_name}",
                    "processing_stats": {
                        "chunk_count": chunk_count,
                        "elapsed_time": round(elapsed_time, 2),
                        "content_length": len(full_content),
                        "avg_chunks_per_second": round(chunk_count/elapsed_time, 2) if elapsed_time > 0 else 0,
                        "provider": "Qwen",
                        "gpu_memory_used": torch.cuda.memory_allocated() / 1024**3 if torch.cuda.is_available() else 0
                    }
                }

            except asyncio.CancelledError:
                elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
                logger.warning(f"🔄 [{self.session_id}] Qwen 답변이 새로운 토큰으로 인해 중단됨 ({elapsed_time:.2f}초 후)")
                logger.info(f"📊 [{self.session_id}] 중단 시점 통계: {chunk_count if 'chunk_count' in locals() else 0}개 청크 처리됨")
                return {
                    "type": "aborted",
                    "message": "새로운 입력으로 인해 중단됨",
                    "partial_content": full_content if 'full_content' in locals() else "",
                    "timestamp": datetime.now().isoformat(),
                    "model_used": f"Qwen {self.model_name}",
                    "processing_stats": {
                        "chunk_count": chunk_count if 'chunk_count' in locals() else 0,
                        "elapsed_time": round(elapsed_time, 2),
                        "content_length": len(full_content) if 'full_content' in locals() else 0,
                        "provider": "Qwen"
                    }
                }
            except Exception as error:
                elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
                logger.error(f"💥 [{self.session_id}] Qwen 답변 생성 중 오류: {error} ({elapsed_time:.2f}초 후)")

                # Qwen 특화 에러 처리
                error_type = "unknown"
                if "cuda" in str(error).lower() or "gpu" in str(error).lower():
                    error_type = "gpu_error"
                elif "memory" in str(error).lower():
                    error_type = "memory_error"
                elif "model" in str(error).lower():
                    error_type = "model_error"
                elif "timeout" in str(error).lower():
                    error_type = "timeout"
                elif "concatenate" in str(error).lower():
                    error_type = "string_concatenation_error"

                return {
                    "type": "error",
                    "error": str(error),
                    "error_type": error_type,
                    "timestamp": datetime.now().isoformat(),
                    "model_used": f"Qwen {self.model_name}",
                    "processing_stats": {
                        "chunk_count": chunk_count if 'chunk_count' in locals() else 0,
                        "elapsed_time": round(elapsed_time, 2),
                        "provider": "Qwen"
                    }
                }

        logger.info(f"🎬 [{self.session_id}] Qwen 비동기 태스크 생성 및 시작")
        self.current_task = asyncio.create_task(_generate())
        return await self.current_task

    def reset(self):
        """현재 상태 초기화"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        self.current_question = ""
        self.current_task = None
        self.cancel_event.clear()
        self.is_eos_received = False
        logger.info("Qwen 프로세서가 초기화되었습니다.")


sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
try:
    from shared.infrastructure.http_client import http_client
except ImportError:
    import requests
    http_client = None

class ChatConsumer(AsyncWebsocketConsumer):
    """Django Channels WebSocket Consumer for Chat - Qwen 버전"""

    # 클래스 레벨에서 모든 클라이언트의 프로세서 관리
    processors = {}

    async def connect(self):
        """WebSocket 연결 수락"""
        try:
            headers = dict(self.scope['headers'])
            phone_Id = headers.get(b'phone-id', b'').decode()
            session_Id = headers.get(b'session-id', b'').decode()

            await self.accept()

            self.phone_Id = phone_Id or f"unknown_{id(self)}"  # 🔥 기본값 설정
            self.session_id = session_Id or f"session_{id(self)}"  # 🔥 기본값 설정
            self.is_connected = True  # 🔥 연결 상태 플래그 추가

            logger.info(f"🔗 새 Qwen 클라이언트 연결: {self.phone_Id} (세션: {self.session_id})")

            # Qwen 프로세서 생성
            processor = QwenStreamProcessor(session_id=self.session_id)
            ChatConsumer.processors[self.phone_Id] = processor

            # 연결 확인 메시지 전송 - Qwen 정보 포함
            await self.safe_send({
                "type": "connection_established",
                "phone_Id": self.phone_Id,
                "session_id": self.session_id,
                "message": "Qwen WebSocket 연결이 성공적으로 설정되었습니다.",
                "model_info": {
                    "provider": "Qwen",
                    "model": processor.model_name,
                    "features": ["로컬 추론", "스트리밍", "대화 기록", "한국어 특화"],
                    "gpu_available": torch.cuda.is_available(),
                    "model_ready": qwen_model.is_ready if qwen_model else False
                },
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"[{self.phone_Id}] Qwen 연결 초기화 완료")

        except Exception as e:
            logger.error(f"❌ WebSocket 연결 중 오류: {e}")
            self.is_connected = False
            try:
                await self.close()
            except:
                pass

    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        phone_id = getattr(self, 'phone_Id', 'Unknown')
        logger.info(f"Qwen 클라이언트 {phone_id} 연결 종료 (코드: {close_code})")
        self.is_connected = False  # 🔥 연결 상태 false로 변경
        await self.cleanup_client()

    async def receive(self, text_data):
        """메시지 수신 처리"""
        phone_id = getattr(self, 'phone_Id', 'Unknown')
        logger.info(f"[{phone_id}] Qwen 원본 메시지 수신: {repr(text_data)}")

        try:
            # JSON 메시지 파싱
            data = json.loads(text_data)
            logger.info(f"[{phone_id}] JSON 파싱 성공: {data}")
            await self.handle_json_message(data)

        except Exception as e:
            logger.error(f"[{phone_id}] Qwen 메시지 처리 중 오류: {e}")
            await self.safe_send_error(str(e))

    async def handle_json_message(self, data: dict):
        """JSON 형식 메시지 처리"""
        if data.get("token"):
            # 토큰 처리
            token = data.get("token", "")
            request_Id = data.get("request_id", "")
            phone_id = getattr(self, 'phone_Id', 'Unknown')
            logger.info(f"[{phone_id}] Qwen 토큰 처리: '{token}' , request_Id 처리: '{request_Id}'")

            # 비동기로 토큰 처리
            asyncio.create_task(
                self.process_token_and_respond(token, request_Id)
            )

    async def safe_send(self, data: dict):
        """안전한 메시지 전송 - 연결 상태 확인"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            phone_id = getattr(self, 'phone_Id', 'Unknown')
            logger.warning(f"[{phone_id}] WebSocket 연결이 이미 끊어짐 - 메시지 전송 스킵")
            return False
            
        try:
            await self.send(text_data=json.dumps(data, ensure_ascii=False))
            return True
        except RuntimeError as e:
            if "websocket.close" in str(e) or "response already completed" in str(e):
                phone_id = getattr(self, 'phone_Id', 'Unknown')
                logger.warning(f"[{phone_id}] WebSocket 이미 닫힘 - 연결 상태 업데이트")
                self.is_connected = False
                return False
            else:
                phone_id = getattr(self, 'phone_Id', 'Unknown')
                logger.error(f"[{phone_id}] 메시지 전송 오류: {e}")
                raise e
        except Exception as e:
            phone_id = getattr(self, 'phone_Id', 'Unknown')
            logger.error(f"[{phone_id}] 예상치 못한 전송 오류: {e}")
            self.is_connected = False
            return False

    async def process_token_and_respond(self, token: str, request_Id: str):
        """토큰을 처리하고 응답을 전송 - 연결 상태 확인 추가"""
        try:
            # 🔥 연결 상태 사전 확인
            if not hasattr(self, 'is_connected') or not self.is_connected:
                logger.warning(f"[{getattr(self, 'phone_Id', 'Unknown')}] WebSocket 연결 끊어짐 - 토큰 처리 중단")
                return

            processor = ChatConsumer.processors.get(self.phone_Id)
            if not processor:
                logger.error(f"[{self.phone_Id}] Qwen 프로세서를 찾을 수 없습니다.")
                await self.safe_send_error("Qwen 프로세서를 찾을 수 없습니다.")
                return

            start_time = time.time()
            logger.info(f"🎮 [{self.phone_Id}] Qwen 토큰 처리 시작: '{token}'")

            # 🔥 빈 토큰이나 이상한 토큰 체크
            if not token or token.strip() == '':
                logger.warning(f"[{self.phone_Id}] 빈 토큰 수신 - 처리 스킵")
                return

            result = await processor.process_stream_token(token)
            processing_time = time.time() - start_time

            # 🔥 연결 상태 재확인
            if not hasattr(self, 'is_connected') or not self.is_connected:
                logger.warning(f"[{self.phone_Id}] 처리 완료 후 연결 확인 실패 - 응답 전송 스킵")
                return

            # 결과를 클라이언트에게 전송
            response = {
                "phone_Id": self.phone_Id,
                "token_received": token,
                "processing_time": round(processing_time, 3),
                "provider": "Qwen",
                **result
            }

            # 🔥 안전한 전송 사용
            send_success = await self.safe_send(response)
            if not send_success:
                logger.warning(f"[{self.phone_Id}] 응답 전송 실패 - 연결 끊어짐")
                return

            # 🔥 TTS 전송은 tts_required가 True인 경우에만 실행
            if (result["type"] == "complete" and 
                result.get("tts_required", False) and
                result.get('content', '').strip()):
                
                # 🔥 TTS 전송 전에도 연결 상태 확인
                if not hasattr(self, 'is_connected') or not self.is_connected:
                    logger.warning(f"[{self.phone_Id}] TTS 전송 전 연결 확인 실패")
                    return

                # 🔥 빈 답변이나 너무 짧은 답변은 TTS 스킵
                content = result.get('content', '').strip()
                if not content or len(content) < 2:
                    logger.warning(f"[{self.phone_Id}] 답변이 너무 짧아서 TTS 스킵: '{content}'")
                    return

                tts_message = {
                    'phoneId': self.phone_Id,
                    'sessionId': self.session_id,
                    'requestId': request_Id,
                    'voice_config': {'language': 'ko'},
                    'text': content
                }

                stats = result.get("processing_stats", {})
                logger.info(f"🎉 [{self.phone_Id}] Qwen 최종 답변 완료 - TTS 전송!")
                logger.info(f"📝 질문: '{result.get('question', '')}'")
                logger.info(f"📄 답변 길이: {len(content)}자")
                logger.info(f"⏱️ 총 처리 시간: {processing_time:.3f}초")

                # TTS 전송 (비동기로 실행하되 에러 처리)
                asyncio.create_task(self.safe_send_to_tts(tts_message))
                
            elif result["type"] == "complete":
                # 다른 complete 타입들은 로그만 출력
                logger.info(f"📝 [{self.phone_Id}] 답변 완료 (TTS 스킵): {result.get('message', '')}")
                logger.info(f"📄 답변 내용: '{result.get('content', '')[:50]}...'")
                
            elif result["type"] == "aborted":
                stats = result.get("processing_stats", {})
                logger.warning(f"💔 [{self.phone_Id}] Qwen 답변 중단됨")
                logger.info(f"⏱️ 중단까지 시간: {processing_time:.3f}초")
                if stats:
                    logger.info(f"📊 중단 시점 통계: {stats}")

            elif result["type"] == "interrupted":
                logger.info(f"⚡ [{self.phone_Id}] Qwen 실시간 답변 진행 중...")
                logger.info(f"⏱️ 현재까지 처리 시간: {processing_time:.3f}초")

            elif result["type"] == "error":
                error_type = result.get("error_type", "unknown")
                logger.error(f"❌ [{self.phone_Id}] Qwen 처리 오류 ({error_type}): {result.get('error', '')}")
                logger.info(f"⏱️ 오류 발생까지 시간: {processing_time:.3f}초")

        except Exception as e:
            processing_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"💥 [{getattr(self, 'phone_Id', 'Unknown')}] Qwen 토큰 처리 중 예외 발생: {e}")
            logger.info(f"⏱️ 예외 발생까지 시간: {processing_time:.3f}초")
            # 🔥 예외 처리 시 연결 상태 확인 후 에러 전송
            if hasattr(self, 'is_connected') and self.is_connected:
                try:
                    await self.safe_send_error(str(e))
                except:
                    logger.error(f"[{getattr(self, 'phone_Id', 'Unknown')}] 에러 응답 전송도 실패")

    async def safe_send_error(self, error_message: str):
        """안전한 오류 응답 전송"""
        phone_id = getattr(self, 'phone_Id', 'Unknown')
        if not hasattr(self, 'is_connected') or not self.is_connected:
            logger.warning(f"[{phone_id}] 연결 끊어짐 - 오류 메시지 전송 스킵")
            return

        await self.safe_send({
            "type": "error",
            "error": error_message,
            "phone_Id": phone_id,
            "provider": "Qwen",
            "timestamp": datetime.now().isoformat()
        })

    async def cleanup_client(self):
        """클라이언트 연결 정리"""
        phone_id = getattr(self, 'phone_Id', 'Unknown')
        if hasattr(self, 'phone_Id') and self.phone_Id in ChatConsumer.processors:
            processor = ChatConsumer.processors[self.phone_Id]
            processor.reset()  # 진행 중인 작업 정리
            del ChatConsumer.processors[self.phone_Id]
            logger.info(f"Qwen 클라이언트 {phone_id} 정리 완료")

    async def safe_send_to_tts(self, tts_message: Dict[str, Any]):
        """TTS 전송 - 연결 상태 무관하게 실행"""
        try:
            result = await self.send_to_tts_server(tts_message)
            phone_id = getattr(self, 'phone_Id', 'Unknown')
            logger.info(f"📡 [{phone_id}] TTS 전송 결과: {result.get('success', False)}")
        except Exception as e:
            phone_id = getattr(self, 'phone_Id', 'Unknown')
            logger.error(f"❌ [{phone_id}] TTS 전송 중 오류: {e}")

    async def send_to_tts_server(self, tts_message: Dict[str, Any]) -> Dict[str, Any]:
        """TTS 서버로 HTTP POST 전송 - Qwen 버전"""
        self.tts_server_url = getattr(settings, 'TTS_SERVER_URL', 'http://tts_server:5002')
        
        try:
            tts_url = f"{self.tts_server_url}/api/convert-tts/"

            # 전송할 데이터 로깅
            logger.info(f"📤 [Qwen LLM Workflow] TTS 서버로 HTTP 전송: {tts_url}")
            logger.info(f"📦 [Qwen LLM Workflow] 전송 데이터: {tts_message}")

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

                logger.info(f"📡 [Qwen LLM Workflow] 응답 상태코드: {response.status_code}")
                logger.info(f"📄 [Qwen LLM Workflow] 응답 내용: {response.text[:500]}")

                if response.status_code == 200:
                    logger.info("✅ [Qwen LLM Workflow] TTS 서버로 전송 성공!")
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'data': response.json() if response.content else None,
                        'llm_provider': 'Qwen'
                    }
                else:
                    logger.error(f"❌ [Qwen LLM Workflow] TTS 서버 전송 실패: {response.status_code}")
                    logger.error(f"📄 [Qwen LLM Workflow] 오류 응답: {response.text}")
                    return {
                        'success': False,
                        'status_code': response.status_code,
                        'error': response.text,
                        'llm_provider': 'Qwen'
                    }

        except Exception as e:
            logger.error(f"❌ [Qwen LLM Workflow] TTS 서버 전송 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'llm_provider': 'Qwen'
            }