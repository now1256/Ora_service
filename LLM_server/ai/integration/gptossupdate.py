# ai/ask.py
import json
import asyncio
import os
import sys
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque
import concurrent.futures

from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from dotenv import load_dotenv
import logging

# API KEY 정보로드
load_dotenv()
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from ..utils.prompts import prompt

logger = logging.getLogger(__name__)

class TrulyParallelStreamProcessor:
    """🔥 진정한 병렬 처리를 위한 스트림 프로세서"""
    
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.current_question = ""
        
        # 🔥 병렬 처리를 위한 새로운 구조
        self.latest_token_id = 0  # 가장 최신 토큰 ID
        self.result_queue = asyncio.Queue()  # 결과 전송용 큐
        
        # 현재 진행 중인 작업들 추적
        self.preview_tasks = set()  # 활성 미리보기 태스크들
        self.final_task = None  # 최종 답변 태스크
        
        # 마지막 완료된 응답 저장
        self.last_completed_response = ""
        self.last_completed_question = ""
        
        # 🔥 캐시 시스템
        self.preview_cache = {}  # 미리보기 캐시
        
        # Thread executor for blocking operations
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Langchain 설정
        self.setup_langchain()
    
    def setup_langchain(self):
        """Langchain 체인 설정"""
        self.llm = ChatOpenAI(model_name="gpt-4o-mini")

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

    def get_cached_preview(self, question: str) -> Optional[str]:
        """캐시된 미리보기 응답 확인"""
        # 간단한 패턴 매칭
        common_patterns = {
            "이름": "저는 오라입니다.",
            "안녕": "안녕하세요!",
            "날씨": "날씨에 대해 알려드릴게요.",
            "뭐야": "무엇을 도와드릴까요?",
            "누구": "저는 AI 어시스턴트 오라입니다.",
        }
        
        question_lower = question.lower()
        for pattern, response in common_patterns.items():
            if pattern in question_lower:
                return response
        
        return self.preview_cache.get(question)

    def cache_preview(self, question: str, content: str):
        """미리보기 결과 캐시 저장"""
        if len(content) > 10 and len(question) > 2:
            self.preview_cache[question] = content[:100]  # 처음 100자만 저장

    async def process_stream_token(self, token: str) -> Dict[str, Any]:
        """🔥 진정한 병렬 토큰 처리 - 즉시 반환"""
        
        # 토큰 ID 생성 (최신성 추적용)
        self.latest_token_id += 1
        current_token_id = self.latest_token_id
        
        # 🔥 현재 처리 중인 토큰 ID 설정 (스트림 취소용)
        self._processing_token_id = current_token_id
        
        logger.info(f"🎯 [{self.session_id}] 토큰 수신 (ID: {current_token_id}): '{token}'")
        
        if token == '<eos>':
            logger.info(f"🏁 [{self.session_id}] EOS 감지 - 기존 응답 재사용 또는 최종 답변 시작")
            
            # 🔥 현재 질문에 대한 완료된 응답이 있는지 확인
            current_question = self.current_question.strip()
            
            logger.info(f"🔍 [{self.session_id}] 응답 재사용 확인:")
            logger.info(f"🔍 [{self.session_id}] - 현재 질문: '{current_question}'")
            logger.info(f"🔍 [{self.session_id}] - 저장된 질문: '{self.last_completed_question}'")
            logger.info(f"🔍 [{self.session_id}] - 저장된 응답: '{self.last_completed_response[:50]}...' ({len(self.last_completed_response)}자)")
            logger.info(f"🔍 [{self.session_id}] - 질문 일치: {current_question == self.last_completed_question}")
            logger.info(f"🔍 [{self.session_id}] - 응답 존재: {bool(self.last_completed_response)}")
            logger.info(f"🔍 [{self.session_id}] - 진행 중인 미리보기: {len(self.preview_tasks)}개")
            
            # 🔥 이미 완료된 응답이 있고 질문이 동일하면 즉시 재사용
            if (self.last_completed_response and 
                self.last_completed_question and
                current_question == self.last_completed_question):
                
                logger.info(f"🔄 [{self.session_id}] 기존 완료된 응답 재사용: '{self.last_completed_response[:50]}...'")
                
                # 🔥 모든 미리보기 작업 즉시 취소
                self._cancel_all_preview_tasks()
                
                # 상태 초기화
                question = current_question
                self.current_question = ""
                
                # 즉시 완료 응답 생성
                result = {
                    "type": "complete",
                    "content": self.last_completed_response,
                    "question": question,
                    "token_id": current_token_id,
                    "processing_time": 0.001,  # 즉시 처리
                    "timestamp": datetime.now().isoformat(),
                    "message": "기존 완료된 응답 재사용",
                    "processing_stats": {
                        "type": "reused",
                        "elapsed_time": 0.001,
                        "content_length": len(self.last_completed_response),
                        "source": "cache"
                    }
                }
                
                # 백그라운드로 즉시 전송
                asyncio.create_task(self._send_immediate_result(result))
                
                return {
                    "type": "eos_received",
                    "message": "기존 응답 재사용 중...",
                    "question": question,
                    "token_id": current_token_id,
                    "timestamp": datetime.now().isoformat()
                }
            
            # 🔥 진행 중인 미리보기 태스크가 있으면 완료 대기
            elif self.preview_tasks:
                logger.info(f"⏳ [{self.session_id}] 진행 중인 미리보기 완료 대기: {len(self.preview_tasks)}개")
                
                # 🔥 모든 미리보기 작업 취소하지 않고 완료 대기
                active_tasks = [task for task in self.preview_tasks if not task.done()]
                
                if active_tasks:
                    try:
                        # 🔥 가장 최근 태스크 완료 대기 (최대 1초)
                        latest_task = active_tasks[-1]  # 가장 최신 태스크
                        
                        logger.info(f"⏳ [{self.session_id}] 최신 미리보기 완료 대기 중... (최대 1초)")
                        await asyncio.wait_for(latest_task, timeout=1.0)
                        
                        logger.info(f"✅ [{self.session_id}] 미리보기 완료 대기 완료")
                        
                        # 🔥 완료 후 저장된 응답 확인
                        logger.info(f"🔍 [{self.session_id}] 대기 후 재확인:")
                        logger.info(f"🔍 [{self.session_id}] - 저장된 질문: '{self.last_completed_question}'")
                        logger.info(f"🔍 [{self.session_id}] - 저장된 응답: '{self.last_completed_response[:50]}...' ({len(self.last_completed_response)}자)")
                        
                        if (self.last_completed_response and 
                            self.last_completed_question == current_question):
                            
                            logger.info(f"🔄 [{self.session_id}] 대기 후 완료된 응답 재사용")
                            
                            # 남은 미리보기 작업들 취소
                            self._cancel_all_preview_tasks()
                            
                            # 상태 초기화
                            question = current_question
                            self.current_question = ""
                            
                            result = {
                                "type": "complete",
                                "content": self.last_completed_response,
                                "question": question,
                                "token_id": current_token_id,
                                "processing_time": 0.001,
                                "timestamp": datetime.now().isoformat(),
                                "message": "미리보기 완료 후 응답 재사용",
                                "processing_stats": {
                                    "type": "reused_after_wait",
                                    "elapsed_time": 0.001,
                                    "content_length": len(self.last_completed_response),
                                    "source": "completed_preview"
                                }
                            }
                            
                            asyncio.create_task(self._send_immediate_result(result))
                            
                            return {
                                "type": "eos_received",
                                "message": "미리보기 완료 후 응답 재사용",
                                "question": question,
                                "token_id": current_token_id,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"⏰ [{self.session_id}] 미리보기 대기 타임아웃 (1초) - 새 답변 생성")
                        # 타임아웃 시 미리보기 취소하고 새로 생성
                        self._cancel_all_preview_tasks()
                    except asyncio.CancelledError:
                        logger.info(f"🔄 [{self.session_id}] 미리보기 대기 중 취소됨")
                        self._cancel_all_preview_tasks()
                    except Exception as e:
                        logger.error(f"❌ [{self.session_id}] 미리보기 대기 중 오류: {e}")
                        self._cancel_all_preview_tasks()
                else:
                    logger.info(f"✅ [{self.session_id}] 진행 중인 미리보기 없음")
            
            # 🔥 모든 미리보기 작업 취소
            self._cancel_all_preview_tasks()
            
            # 🔥 완료된 응답이 없으면 최종 답변을 백그라운드에서 처리 (논블로킹)
            if current_question:
                logger.info(f"🚀 [{self.session_id}] 새로운 최종 답변 생성 시작 (응답 없음)")
                self.final_task = asyncio.create_task(
                    self._generate_final_response_background(current_token_id)
                )
                
                return {
                    "type": "eos_received",
                    "message": "최종 답변 생성 중...",
                    "question": current_question,
                    "token_id": current_token_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "type": "complete",
                    "content": "질문을 입력해주세요.",
                    "question": "",
                    "token_id": current_token_id,
                    "message": "빈 질문으로 EOS 수신",
                    "timestamp": datetime.now().isoformat()
                }
        
        else:
            # 🔥 일반 토큰 처리 - 완전 논블로킹
            
            # 질문 업데이트
            old_question = self.current_question
            self.current_question += token
            
            logger.info(f"📝 [{self.session_id}] 질문 업데이트 (ID: {current_token_id}): '{old_question}' → '{self.current_question}'")
            
            # 🔥 질문이 변경되었으므로 기존 완료된 응답 무효화
            if old_question != self.current_question:
                self.last_completed_response = ""
                self.last_completed_question = ""
                logger.info(f"🗑️ [{self.session_id}] 질문 변경으로 기존 응답 캐시 무효화")
            
            # 🔥 이전 미리보기들 즉시 취소 (기다리지 않음)
            self._cancel_all_preview_tasks()
            
            # 🔥 새 미리보기를 백그라운드에서 시작 (논블로킹)
            if len(self.current_question.strip()) > 2:  # 2자 이상부터 미리보기
                logger.info(f"👁️ [{self.session_id}] 실시간 미리보기 생성 시작 (ID: {current_token_id})")
                preview_task = asyncio.create_task(
                    self._generate_preview_background(current_token_id)
                )
                self.preview_tasks.add(preview_task)
                
                # 완료된 태스크 자동 정리를 위한 콜백
                preview_task.add_done_callback(
                    lambda t: self.preview_tasks.discard(t)
                )
            
            # 🔥 즉시 반환 - 입력 상태만 전송
            return {
                "type": "typing",
                "current_question": self.current_question,
                "message": "입력 중...",
                "token_id": current_token_id,
                "timestamp": datetime.now().isoformat()
            }

    def _cancel_all_preview_tasks(self):
        """🔥 모든 미리보기 작업 즉시 취소 (논블로킹)"""
        cancelled_count = 0
        for task in list(self.preview_tasks):
            if not task.done():
                task.cancel()
                cancelled_count += 1
        
        if cancelled_count > 0:
            logger.info(f"🛑 [{self.session_id}] {cancelled_count}개 미리보기 작업 취소됨")

    async def _generate_preview_background(self, token_id: int):
        """🔥 백그라운드 미리보기 생성 - 진정한 실시간 중단"""
        try:
            start_time = time.time()
            
            # 최신 토큰인지 확인 (취소되지 않았다면)
            if token_id != self.latest_token_id:
                logger.info(f"🔄 [{self.session_id}] 미리보기 중단 (ID: {token_id}) - 더 새로운 토큰 존재")
                return
            
            logger.info(f"🚀 [{self.session_id}] 미리보기 생성 시작 (ID: {token_id}) - 질문: '{self.current_question}'")
            
            # 🔥 현재 질문 저장 (변수 변경 방지)
            current_question_snapshot = self.current_question
            
            # 🔥 캐시된 응답 먼저 확인
            cached_response = self.get_cached_preview(current_question_snapshot)
            if cached_response:
                logger.info(f"⚡ [{self.session_id}] 캐시된 미리보기 사용: '{cached_response}'")
                content = cached_response
                elapsed_time = 0.001
                
                # 🔥 캐시된 응답도 last_completed_response에 즉시 저장!
                self.last_completed_response = content.strip()
                self.last_completed_question = current_question_snapshot
                logger.info(f"💾 [{self.session_id}] 캐시된 미리보기를 완료된 응답으로 저장")
                
            else:
                # 🔥 더 짧은 타임아웃으로 빠른 응답
                try:
                    content = await asyncio.wait_for(
                        self._generate_limited_stream(current_question_snapshot, max_chunks=1),  # 1개 청크로 더 빠르게
                        timeout=0.5  # 0.5초 타임아웃으로 단축
                    )
                    
                    logger.info(f"🎯 [{self.session_id}] 생성된 미리보기 내용: '{content}'")
                    
                except asyncio.TimeoutError:
                    logger.info(f"⏰ [{self.session_id}] 미리보기 타임아웃 (ID: {token_id}) - 0.5초 제한")
                    content = "생각 중..."
                
                elapsed_time = time.time() - start_time
                
                # 🔥 빠른 응답만 캐시에 저장
                if elapsed_time < 0.3 and len(content) > 10:
                    self.cache_preview(current_question_snapshot, content)
                
                # 🔥 생성된 미리보기를 last_completed_response에 저장 (조건 완화)
                if content and content.strip() and content != "생각 중..." and len(content.strip()) > 2:
                    self.last_completed_response = content.strip()
                    self.last_completed_question = current_question_snapshot
                    logger.info(f"💾 [{self.session_id}] 생성된 미리보기를 완료된 응답으로 저장")
                else:
                    logger.warning(f"⚠️ [{self.session_id}] 미리보기 저장 실패 - content: '{content}', 길이: {len(content.strip()) if content else 0}")
            
            # 🔥 여전히 최신 토큰인지 확인
            if token_id != self.latest_token_id:
                logger.info(f"🔄 [{self.session_id}] 미리보기 완료했지만 무시 (ID: {token_id}) - 더 새로운 토큰 존재")
                return
            
            # 결과 큐에 추가
            result = {
                "type": "preview",
                "content": content,
                "current_question": current_question_snapshot,
                "token_id": token_id,
                "processing_time": round(elapsed_time, 3),
                "timestamp": datetime.now().isoformat(),
                "processing_stats": {
                    "type": "preview",
                    "elapsed_time": round(elapsed_time, 2),
                    "content_length": len(content),
                    "source": "cache" if cached_response else "generated"
                }
            }
            
            await self.result_queue.put(result)
            logger.info(f"👁️ [{self.session_id}] 미리보기 완료 (ID: {token_id}, {elapsed_time:.2f}초)")
            
            # 🔥 저장 상태 확인 로그
            logger.info(f"🔍 [{self.session_id}] 저장 확인 - 질문: '{self.last_completed_question}', 응답: '{self.last_completed_response[:30]}...' ({len(self.last_completed_response)}자)")
            
        except asyncio.CancelledError:
            logger.info(f"🔄 [{self.session_id}] 미리보기 취소됨 (ID: {token_id})")
        except Exception as e:
            logger.error(f"❌ [{self.session_id}] 미리보기 생성 오류 (ID: {token_id}): {e}")
            import traceback
            logger.error(f"❌ [{self.session_id}] 상세 오류: {traceback.format_exc()}")

    async def _generate_final_response_background(self, token_id: int):
        """🔥 백그라운드 최종 답변 생성"""
        try:
            start_time = time.time()
            question = self.current_question  # 현재 질문 저장
            
            logger.info(f"🎯 [{self.session_id}] 최종 답변 생성 시작 (ID: {token_id}): '{question}'")
            
            # 🔥 질문이 비어있는지 확인
            if not question or not question.strip():
                logger.warning(f"⚠️ [{self.session_id}] 최종 답변 생성 중단: 질문이 비어있음")
                
                error_result = {
                    "type": "complete",
                    "content": "질문을 입력해주세요.",
                    "question": question,
                    "token_id": token_id,
                    "timestamp": datetime.now().isoformat(),
                    "message": "빈 질문으로 인한 기본 응답",
                    "processing_stats": {
                        "type": "fallback",
                        "elapsed_time": 0.001,
                        "content_length": 12
                    }
                }
                await self.result_queue.put(error_result)
                return
            
            # 🔥 완전한 답변 생성 (제한 없음)
            content = await self._generate_complete_stream(question)
            
            elapsed_time = time.time() - start_time
            
            # 🔥 생성된 답변 검증
            if not content or not content.strip():
                logger.warning(f"⚠️ [{self.session_id}] 생성된 답변이 비어있음: '{content}'")
                content = "죄송합니다. 답변을 생성할 수 없었습니다."
            
            # 완료된 응답 저장
            if content.strip():
                self.last_completed_response = content.strip()
                self.last_completed_question = question
                logger.info(f"💾 [{self.session_id}] 최종 응답 저장됨")
            
            # 결과 큐에 추가
            result = {
                "type": "complete",
                "content": content.strip(),
                "question": question,
                "token_id": token_id,
                "processing_time": round(elapsed_time, 3),
                "timestamp": datetime.now().isoformat(),
                "message": "EOS로 인한 최종 답변 완료",
                "processing_stats": {
                    "type": "final",
                    "elapsed_time": round(elapsed_time, 2),
                    "content_length": len(content.strip())
                }
            }
            
            await self.result_queue.put(result)
            logger.info(f"✅ [{self.session_id}] 최종 답변 완료 (ID: {token_id}, {elapsed_time:.2f}초)")
            logger.info(f"📄 [{self.session_id}] 최종 응답 길이: {len(content.strip())}자")
            logger.info(f"📄 [{self.session_id}] 최종 응답 내용: '{content.strip()[:100]}{'...' if len(content.strip()) > 100 else ''}'")
            
            # 상태 초기화
            self.current_question = ""
            
        except Exception as e:
            logger.error(f"❌ [{self.session_id}] 최종 답변 생성 오류 (ID: {token_id}): {e}")
            
            # 오류 결과도 큐에 추가
            error_result = {
                "type": "complete",
                "content": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "question": self.current_question,
                "token_id": token_id,
                "timestamp": datetime.now().isoformat(),
                "message": "답변 생성 중 오류 발생",
                "processing_stats": {"error": str(e)}
            }
            await self.result_queue.put(error_result)

    async def _generate_limited_stream(self, question: str, max_chunks: int = 1) -> str:
        """🔥 제한된 청크로 빠른 미리보기 생성"""
        content = ""
        chunk_count = 0
        
        try:
            logger.info(f"🚀 [{self.session_id}] 제한된 스트림 시작: '{question}' (최대 {max_chunks}개 청크)")
            
            # 🔥 executor를 통한 논블로킹 스트림 처리
            chunks = await self._get_stream_chunks_async(question, max_chunks)
            
            for chunk in chunks:
                if chunk:
                    content += str(chunk)
                    chunk_count += 1
                
                # 취소 확인
                await asyncio.sleep(0)  # yield control
            
            if chunk_count >= max_chunks:
                content += "..."
            
            logger.info(f"📏 [{self.session_id}] 제한된 스트림 완료: {chunk_count}개 청크")
        
        except asyncio.CancelledError:
            logger.info(f"🔄 [{self.session_id}] 제한된 스트림 취소됨")
            raise
        except Exception as e:
            logger.error(f"❌ [{self.session_id}] 제한된 스트림 오류: {e}")
        
        return content.strip() or "생각 중..."

    async def _generate_complete_stream(self, question: str) -> str:
        """🔥 완전한 답변 생성"""
        content = ""
        chunk_count = 0
        
        try:
            logger.info(f"🎯 [{self.session_id}] 완전한 스트림 시작: '{question}'")
            
            # 🔥 질문 검증
            if not question or not question.strip():
                logger.warning(f"⚠️ [{self.session_id}] 빈 질문으로 기본 응답 반환")
                return "무엇을 도와드릴까요?"
            
            # 🔥 executor를 통한 논블로킹 스트림 처리
            chunks = await self._get_stream_chunks_async(question, max_chunks=None)
            
            for chunk in chunks:
                if chunk:
                    content += str(chunk)
                    chunk_count += 1
                
                # 주기적으로 control yield
                if chunk_count % 5 == 0:
                    await asyncio.sleep(0)
            
            logger.info(f"✅ [{self.session_id}] 완전한 스트림 완료: {chunk_count}개 청크")
            
            # 🔥 결과 검증 및 후처리
            final_content = content.strip()
            if not final_content:
                logger.warning(f"⚠️ [{self.session_id}] 스트림 결과가 비어있음, 기본 응답 사용")
                final_content = "답변을 생성하는 데 문제가 있었습니다. 다시 시도해주세요."
            
            logger.info(f"📄 [{self.session_id}] 최종 내용 미리보기: '{final_content[:100]}{'...' if len(final_content) > 100 else ''}'")
            
            return final_content
        
        except Exception as e:
            logger.error(f"❌ [{self.session_id}] 완전한 스트림 생성 오류: {e}")
            return "죄송합니다. 답변 생성 중 오류가 발생했습니다."

    async def _get_stream_chunks_async(self, question: str, max_chunks: Optional[int] = None) -> list:
        """🔥 진정한 비동기 LangChain 스트림 처리 - 실시간 취소 지원"""
        loop = asyncio.get_event_loop()
        
        def sync_stream_with_cancel_check():
            """취소 확인이 가능한 동기 스트림 실행"""
            try:
                chunks = []
                chunk_count = 0
                
                # 🔥 스트림 iterator 생성
                stream_iter = self.chain_with_history.stream(
                    {"input": question},
                    config={"configurable": {"session_id": self.session_id}}
                )
                
                # 🔥 청크별로 취소 확인하면서 처리
                for chunk in stream_iter:
                    # 🔥 매 청크마다 최신 토큰 ID 확인 (실시간 취소)
                    if hasattr(self, '_current_processing_id'):
                        if getattr(self, '_processing_token_id', 0) != self._current_processing_id:
                            logger.info(f"🔄 [{self.session_id}] 스트림 중단됨 - 새 토큰으로 인한 취소")
                            break  # 즉시 중단
                    
                    if chunk:
                        chunks.append(chunk)
                        chunk_count += 1
                        
                        # 🔥 청크 처리 후에도 취소 확인
                        if hasattr(self, '_current_processing_id'):
                            if getattr(self, '_processing_token_id', 0) != self._current_processing_id:
                                logger.info(f"🔄 [{self.session_id}] 청크 처리 후 중단됨")
                                break
                        
                        # 최대 청크 수 제한
                        if max_chunks and chunk_count >= max_chunks:
                            logger.info(f"📏 [{self.session_id}] 최대 청크 제한 도달: {max_chunks}")
                            break
                
                return chunks
            except Exception as e:
                logger.error(f"❌ [{self.session_id}] 동기 스트림 오류: {e}")
                return []
        
        # 🔥 현재 처리 중인 토큰 ID 설정
        self._current_processing_id = getattr(self, '_processing_token_id', 0)
        
        # 🔥 executor를 사용하여 논블로킹 실행
        try:
            # 더 작은 timeout으로 빠른 응답
            chunks = await asyncio.wait_for(
                loop.run_in_executor(self.executor, sync_stream_with_cancel_check),
                timeout=2.0  # 2초 타임아웃
            )
            return chunks
        except asyncio.TimeoutError:
            logger.warning(f"⏰ [{self.session_id}] 스트림 타임아웃")
            return []

    async def _send_immediate_result(self, result: Dict[str, Any]):
        """🔥 즉시 결과 전송"""
        await self.result_queue.put(result)

    async def get_next_result(self) -> Optional[Dict[str, Any]]:
        """🔥 다음 결과 가져오기 (Consumer에서 호출)"""
        try:
            result = await asyncio.wait_for(self.result_queue.get(), timeout=0.01)  # 10ms 타임아웃
            return result
        except asyncio.TimeoutError:
            return None

    def reset(self):
        """현재 상태 초기화"""
        # 🔥 모든 활성 태스크 취소
        self._cancel_all_preview_tasks()
        
        if self.final_task and not self.final_task.done():
            self.final_task.cancel()
        
        # 상태 초기화
        self.current_question = ""
        self.latest_token_id = 0
        
        # 큐 비우기
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logger.info(f"🧹 [{self.session_id}] 프로세서 초기화 완료")

    def cleanup(self):
        """🔥 정리 작업"""
        self.reset()
        
        # Executor 종료
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        
        logger.info(f"🧹 [{self.session_id}] 프로세서 정리 완료")


sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
try:
    from shared.infrastructure.http_client import http_client
except ImportError:
    # 공통 클라이언트를 찾을 수 없는 경우 requests 직접 사용
    import requests
    http_client = None

class ChatConsumer(AsyncWebsocketConsumer):
    """Django Channels WebSocket Consumer for Chat - 진정한 병렬 처리"""
    
    # 클래스 레벨에서 모든 클라이언트의 프로세서 관리
    processors = {}
    
    async def connect(self):
        """WebSocket 연결 수락"""
        headers = dict(self.scope['headers'])
        phone_Id = headers.get(b'phone-id', b'').decode()
        session_Id = headers.get(b'session-id', b'').decode()
       
        await self.accept()
        
        # 클라이언트 고유 ID 생성
        self.phone_Id = phone_Id
        self.session_id = session_Id
        self.is_connected = True  # 연결 상태 추가
      
        # 🔥 새로운 병렬 프로세서 생성
        processor = TrulyParallelStreamProcessor(session_id=self.session_id)
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
        
        # 🔥 백그라운드 결과 모니터링 시작
        asyncio.create_task(self._monitor_background_results())
        
        logger.info(f"[{self.phone_Id}] 연결 초기화 완료")

    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        logger.info(f"클라이언트 {self.phone_Id} 연결 종료 (코드: {close_code})")
        self.is_connected = False  # 연결 상태 변경
        await self.cleanup_client()

    def is_websocket_connected(self) -> bool:
        """WebSocket 연결 상태 확인"""
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
        """🔥 메시지 수신 처리 - 완전 논블로킹"""
        logger.info(f"[{self.phone_Id}] 원본 메시지 수신: {repr(text_data)}")
        
        try:
            # 🔥 JSON 파싱 전 기본 검증
            if not text_data or not text_data.strip():
                logger.warning(f"[{self.phone_Id}] 빈 메시지 수신됨")
                return
                
            # 🔥 JSON 형식 기본 검증
            text_data = text_data.strip()
            if not (text_data.startswith('{') and text_data.endswith('}')):
                logger.error(f"[{self.phone_Id}] 잘못된 JSON 형식: {repr(text_data)}")
                await self.send_error_response("잘못된 메시지 형식")
                return
            
            # JSON 메시지 파싱
            data = json.loads(text_data)
            logger.info(f"[{self.phone_Id}] JSON 파싱 성공: {data}")
            
            # 🔥 즉시 처리 후 바로 반환 (블로킹 없음)
            await self.handle_json_message(data)
            # receive 메서드가 즉시 완료되어 다음 메시지를 받을 수 있음
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.phone_Id}] JSON 파싱 오류: {e}")
            logger.error(f"[{self.phone_Id}] 문제가 된 텍스트: {repr(text_data)}")
            # 🔥 오류 응답도 논블로킹으로 처리
            asyncio.create_task(self.send_error_response(f"JSON 파싱 오류: {str(e)}"))
        except Exception as e:
            logger.error(f"[{self.phone_Id}] 메시지 처리 중 오류: {e}")
            # 🔥 오류 응답도 논블로킹으로 처리
            asyncio.create_task(self.send_error_response(str(e)))

    async def handle_json_message(self, data: dict):
        """🔥 JSON 형식 메시지 처리 - 완전 논블로킹"""
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
        """🔥 완전히 논블로킹 토큰 처리"""
        if not self.is_websocket_connected():
            logger.warning(f"[{self.phone_Id}] 연결이 끊어져 토큰 처리를 중단합니다: '{token}'")
            return
            
        processor = ChatConsumer.processors.get(self.phone_Id)
        if not processor:
            logger.error(f"[{self.phone_Id}] 프로세서를 찾을 수 없습니다.")
            await self.send_error_response("프로세서를 찾을 수 없습니다.")
            return
        
        start_time = time.time()
        logger.info(f"🎮 [{self.phone_Id}] 토큰 처리 시작: '{token}' (완전 병렬)")
        
        try:
            # 🔥 토큰 처리를 병렬로 즉시 시작 (블로킹 없음)
            result = await processor.process_stream_token(token)
            processing_time = time.time() - start_time
            
            # 결과를 클라이언트에게 즉시 전송
            response = {
                "phone_Id": self.phone_Id,
                "token_received": token,
                "processing_time": round(processing_time, 3),
                **result
            }
            
            # 안전한 전송
            success = await self.safe_send(response)
            if not success:
                logger.warning(f"[{self.phone_Id}] 즉시 응답 전송 실패")
            
            logger.info(f"⚡ [{self.phone_Id}] 즉시 응답 전송 완료: {result['type']} ({processing_time:.3f}초)")
            
        except asyncio.CancelledError:
            processing_time = time.time() - start_time
            logger.info(f"🔄 [{self.phone_Id}] 토큰 처리 취소됨: '{token}' ({processing_time:.3f}초)")
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"💥 [{self.phone_Id}] 토큰 처리 중 예외 발생: {e}")
            logger.info(f"⏱️ 예외 발생까지 시간: {processing_time:.3f}초")
            
            if self.is_websocket_connected():
                await self.send_error_response(str(e))

    async def _monitor_background_results(self):
        """🔥 백그라운드 결과 모니터링 - 지속적으로 실행"""
        processor = ChatConsumer.processors.get(self.phone_Id)
        if not processor:
            logger.error(f"[{self.phone_Id}] 결과 모니터링: 프로세서를 찾을 수 없습니다.")
            return
        
        logger.info(f"🔍 [{self.phone_Id}] 백그라운드 결과 모니터링 시작")
        
        while self.is_websocket_connected():
            try:
                result = await processor.get_next_result()
                if result is None:
                    await asyncio.sleep(0.01)  # 10ms 대기
                    continue
                
                logger.info(f"📤 [{self.phone_Id}] 백그라운드 결과 수신: {result['type']} (ID: {result['token_id']})")
                
                # 결과 전송
                response = {
                    "phone_Id": self.phone_Id,
                    **result
                }
                
                success = await self.safe_send(response)
                if not success:
                    logger.warning(f"[{self.phone_Id}] 백그라운드 결과 전송 실패")
                    break
                
                # 완료된 답변이면 TTS 전송
                if result["type"] == "complete":
                    # 🔥 텍스트 내용 검증 및 정리
                    content = result.get('content', '').strip()
                    
                    stats = result.get("processing_stats", {})
                    logger.info(f"🎉 [{self.phone_Id}] 최종 답변 완료!")
                    logger.info(f"📝 질문: '{result.get('question', '')}'")
                    logger.info(f"📄 답변 길이: {len(content)}자")
                    logger.info(f"📄 답변 내용: '{content[:100]}{'...' if len(content) > 100 else ''}'")
                    logger.info(f"⏱️ 총 처리 시간: {result.get('processing_time', 0)}초")
                    
                    # 🔥 텍스트가 비어있지 않은 경우에만 TTS 전송
                    if content and len(content) > 0:
                        tts_message = {
                            'phoneId': self.phone_Id,
                            'sessionId': self.session_id,
                            'requestId': "background_result",  # request_Id가 없는 경우
                            'voice_config': {'language': 'ko'},
                            'text': content
                        }
                        
                        logger.info(f"📤 [{self.phone_Id}] TTS 전송할 텍스트: '{content}'")
                        
                        # 🔥 TTS 전송 (논블로킹)
                        asyncio.create_task(self._send_to_tts_async(tts_message))
                    else:
                        logger.warning(f"⚠️ [{self.phone_Id}] TTS 전송 중단: 텍스트가 비어있음")
                        logger.warning(f"⚠️ [{self.phone_Id}] 원본 content: '{result.get('content', '')}'")
                        logger.warning(f"⚠️ [{self.phone_Id}] result 전체: {result}")
                    
                elif result["type"] == "preview":
                    logger.info(f"👁️ [{self.phone_Id}] 실시간 미리보기 전송 완료 (병렬)")
                    
            except Exception as e:
                logger.error(f"❌ [{self.phone_Id}] 백그라운드 결과 모니터링 오류: {e}")
                await asyncio.sleep(0.1)
        
        logger.info(f"🔍 [{self.phone_Id}] 백그라운드 결과 모니터링 종료")

    async def _send_to_tts_async(self, tts_message: Dict[str, Any]):
        """🔥 비동기 TTS 전송"""
        try:
            logger.info(f"📡 [{self.phone_Id}] TTS 전송 시작 (비동기)")
            
            # TTS 전송을 별도 executor에서 실행
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.send_to_tts_server, tts_message)
            
            logger.info(f"✅ [{self.phone_Id}] TTS 전송 완료: {result}")
            
        except Exception as e:
            logger.error(f"❌ [{self.phone_Id}] TTS 전송 오류: {e}")

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
            processor.cleanup()  # 진행 중인 작업 정리
            del ChatConsumer.processors[self.phone_Id]
            logger.info(f"클라이언트 {self.phone_Id} 정리 완료")

    def send_to_tts_server(self, tts_message: Dict[str, Any]) -> Dict[str, Any]:
        """TTS 서버로 HTTP POST 전송 (동기 함수 - executor에서 실행됨)"""
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

    async def send_to_external_server(self, tts_message: Dict[str, Any]) -> Dict[str, Any]:
        """TTS 서버로 HTTP POST 전송 (비동기 버전)"""
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