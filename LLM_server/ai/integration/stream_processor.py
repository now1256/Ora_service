# ai/stream_processor.py
import json
import asyncio
import os
import sys
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from django.conf import settings
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


logger = logging.getLogger(__name__)

# 전역 캐시
_rag_manager = None
_user_systems_cache = {}
_json_managers_cache = {}

class LangchainStreamProcessor:
    def __init__(self, session_id: str = "default_session", phone_id: str = "default_session"):
        self.session_id = session_id
        self.phone_Id = phone_id
        self.current_question = ""
        self.is_processing = False
        self.current_task: Optional[asyncio.Task] = None
        self.cancel_event = threading.Event()
        self.is_eos_received = False
      
        # 마지막 완료된 응답 저장
        self.last_completed_response = ""
        self.last_completed_question = ""
        
        # Langchain 설정
        self.user_rag_system = _user_systems_cache.get(self.phone_Id)  

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
                    
                    # EOS 처리 완료 후 상태 초기화 (TTS 전송 전에)
                    self.current_question = ""
                    self.is_eos_received = False
                    self.current_task = None
                    
                    return {
                        "type": "complete",
                        "content": result.get("content", ""),
                        "question": question,
                        "message": "EOS로 인한 완전한 답변 완료",
                        "timestamp": datetime.now().isoformat(),
                        "processing_stats": result.get("processing_stats", {})
                    }
                except Exception as e:
                    logger.error(f"❌ [{self.session_id}] EOS 처리 중 오류: {e}")
                    return {
                        "type": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                # 진행 중인 태스크가 없는 경우 - 마지막 완료된 응답 반환
                if self.last_completed_response:
                    
                    # 마지막 완료된 응답 반환 후 current_question 초기화
                    question = self.last_completed_question
                    self.current_question = ""
                    self.is_eos_received = False
                    
                    return {
                        "type": "complete",
                        "content": self.last_completed_response,
                        "question": question,
                        "message": "마지막 완료된 응답 반환",
                        "timestamp": datetime.now().isoformat()
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
                        "timestamp": datetime.now().isoformat()
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
            logger.info(f"🔄 [{self.session_id}] 새로운 실시간 답변 생성 시작...")
            
            return await self.generate_interruptible_response()

    async def generate_interruptible_response(self) -> Dict[str, Any]:
        """중단 가능한 완전한 답변 생성"""
        
        async def _generate():
            try:
                full_content = ""
                chunk_count = 0
                start_time = time.time()
                
                logger.info(f"🚀 [{self.session_id}] 실시간 답변 생성 시작: '{self.current_question}'")
                
                def run_langchain_stream():
                    try:
                        logger.info(f"📡 [{self.session_id}] Langchain 스트림 호출 중...")
                        
                        if self.user_rag_system:
                            logger.info(f"🔍 [{self.session_id}] RAG 체인으로 스트림 실행")
                            
                            # 중단 이벤트와 EOS 체크 함수 전달
                            for chunk in self.user_rag_system.stream_query(
                                self.current_question, 
                                self.session_id,
                                cancel_event=self.cancel_event,
                                is_eos_received_func=lambda: self.is_eos_received
                            ):
                                # 외부에서는 중단 체크 불필요 (내부에서 처리됨)
                                yield chunk
                        else:
                            logger.error(f"❌ [{self.session_id}] user_rag_system이 없음!")
                            yield "시스템 오류"
                            
                    except Exception as e:
                        logger.error(f"❌ [{self.session_id}] Langchain 스트림 오류: {e}")
                        yield ""
                
                for chunk in run_langchain_stream():
                    if not self.is_eos_received:
                        if self.cancel_event.is_set():
                            logger.warning(f"🛑 [{self.session_id}] 새로운 토큰으로 인한 중단 요청")
                            raise asyncio.CancelledError("새로운 토큰으로 인해 중단됨")
                    
                    if chunk:
                        chunk_count += 1
                        full_content += str(chunk)
                        
                      
                elapsed_time = time.time() - start_time
             

                # 완료된 응답을 저장 (EOS가 아닌 경우에도 저장)
                if full_content.strip():
                    self.last_completed_response = full_content.strip()
                    self.last_completed_question = self.current_question
                    logger.info(f"💾 [{self.session_id}] 완료된 응답 저장됨")

                return {
                    "type": "interrupted" if not self.is_eos_received else "complete",
                    "content": full_content.strip(),
                    "current_question": self.current_question,
                    "timestamp": datetime.now().isoformat(),
                    "processing_stats": {
                        "chunk_count": chunk_count,
                        "elapsed_time": round(elapsed_time, 2),
                        "content_length": len(full_content)
                    }
                }

            except asyncio.CancelledError:
                elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
                logger.warning(f"🔄 [{self.session_id}] 답변이 새로운 토큰으로 인해 중단됨 ({elapsed_time:.2f}초 후)")
                logger.info(f"📊 [{self.session_id}] 중단 시점 통계: {chunk_count if 'chunk_count' in locals() else 0}개 청크 처리됨")
                return {
                    "type": "aborted",
                    "message": "새로운 입력으로 인해 중단됨",
                    "partial_content": full_content if 'full_content' in locals() else "",
                    "timestamp": datetime.now().isoformat(),
                    "processing_stats": {
                        "chunk_count": chunk_count if 'chunk_count' in locals() else 0,
                        "elapsed_time": round(elapsed_time, 2),
                        "content_length": len(full_content) if 'full_content' in locals() else 0
                    }
                }
            except Exception as error:
                elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
                logger.error(f"💥 [{self.session_id}] 답변 생성 중 오류: {error} ({elapsed_time:.2f}초 후)")
                return {
                    "type": "error",
                    "error": str(error),
                    "timestamp": datetime.now().isoformat(),
                    "processing_stats": {
                        "chunk_count": chunk_count if 'chunk_count' in locals() else 0,
                        "elapsed_time": round(elapsed_time, 2)
                    }
                }

        logger.info(f"🎬 [{self.session_id}] 비동기 태스크 생성 및 시작")
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
        # 마지막 완료된 응답은 유지 (세션이 계속될 수 있으므로)
        # self.last_completed_response = ""
        # self.last_completed_question = ""
        logger.info("프로세서가 초기화되었습니다.")

    def save_completed_conversation(self, question: str, response: str):
        """완성된 대화만 저장 (EOS 처리된 경우에만 호출)"""
        if question.strip() and response.strip():
            self.last_completed_question = question.strip()
            self.last_completed_response = response.strip()
            logger.info(f"💾 [{self.session_id}] 완성된 대화 업데이트됨")


# 캐시 및 매니저 관리 함수들
from ..utils.RAG.JSONChatManager import JSONChatManager
from ..utils.RAG.MultiUserRAGManager import MultiUserRAGManager

def get_or_create_rag_manager():
    """RAG 매니저 싱글톤"""
    global _rag_manager
    if _rag_manager is None:
        print("🔄 RAG 매니저 최초 생성")
        _rag_manager = MultiUserRAGManager()
    return _rag_manager

def get_or_create_user_system(phoneId: str):
    """사용자별 RAG 시스템 캐싱"""
    global _user_systems_cache
    
    if phoneId not in _user_systems_cache:
        print(f"🔄 사용자 {phoneId} RAG 시스템 최초 생성")
        rag_manager = get_or_create_rag_manager()
        user_system = rag_manager.get_user_rag_system(phoneId)
        _user_systems_cache[phoneId] = user_system
    else:
        print(f"✅ 사용자 {phoneId} RAG 시스템 캐시에서 로드")

def get_or_create_json_manager(phoneId: str):
    """JSON 매니저 캐싱"""
    global _json_managers_cache
    
    if phoneId not in _json_managers_cache:
        print(f"🔄 사용자 {phoneId} JSON 매니저 최초 생성")
        _json_managers_cache[phoneId] = JSONChatManager(phoneId)
    else:
        print(f"✅ 사용자 {phoneId} JSON 매니저 캐시에서 로드")

def group_messages_into_pairs(messages):
    """메시지를 human-ai 쌍으로 그룹화"""
    pairs = []
    current_human = None
    
    for msg in messages:
        if msg['type'] == 'human':
            current_human = msg
        elif msg['type'] == 'ai' and current_human:
            pairs.append((current_human, msg))
            current_human = None
    
    return pairs