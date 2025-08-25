"""
🚀 현업 레벨 스트리밍 LangChain 처리
Cold Start 문제 해결을 위한 최적화된 스트리밍 LLM
"""
import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from django.core.cache import cache
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import AsyncCallbackHandler
import os

logger = logging.getLogger(__name__)

class StreamingCallback(AsyncCallbackHandler):
    """스트리밍 콜백 핸들러"""
    
    def __init__(self):
        self.tokens = []
        self.start_time = time.time()
        
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """새 토큰 수신시 호출"""
        self.tokens.append(token)
        
class OptimizedStreamingLLM:
    """🚀 현업용 최적화 스트리밍 LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # 🚀 준실시간 스트리밍 - 첫 토큰 극속 (0.2초 목표)
        self.fast_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=self.api_key,
            streaming=True,
            max_tokens=150,  # 완전한 답변 보장 (20 → 150자)
            timeout=3,       # 안정성 확보
            max_retries=0,   # 재시도 없음
            request_timeout=2  # 안정적 요청
        )
        
        # ⚡ 백그라운드도 빠르게 (필요시에만)
        self.accurate_llm = ChatOpenAI(
            model="gpt-4o-mini",  # 정확성보다 속도 우선
            temperature=0,
            api_key=self.api_key,
            max_tokens=50,        # 백그라운드도 짧게
            timeout=5,            # 빠른 타임아웃
            max_retries=0         # 재시도 없음
        )
        
        # 캐시 설정
        self.similarity_threshold = 0.88  # 유사도 임계값
        self.cache_ttl = 900  # 15분

    async def get_instant_response(self, phone_id: str, user_text: str) -> Dict[str, Any]:
        """⚡ 즉시 응답 (0.1초 이내)"""
        
        start_time = time.time()
        
        # 1. 완전 일치 캐시 확인
        exact_cache_key = f"llm_exact:{phone_id}:{hash(user_text)}"
        cached_response = cache.get(exact_cache_key)
        
        if cached_response:
            return {
                "content": cached_response,
                "source": "exact_cache",
                "processing_time": time.time() - start_time,
                "is_fast": True
            }
        
        # 2. 유사 캐시 확인 (임베딩 없이 키워드 기반)
        similar_response = self._check_keyword_cache(phone_id, user_text)
        if similar_response:
            return {
                "content": similar_response,
                "source": "similar_cache", 
                "processing_time": time.time() - start_time,
                "is_fast": True
            }
        
        
        # 4. 스트리밍 응답 시작
        return await self._start_streaming_response(phone_id, user_text)

    def _check_keyword_cache(self, phone_id: str, user_text: str) -> Optional[str]:
        """키워드 기반 유사 캐시 확인"""
        try:
            # 주요 키워드 추출
            keywords = self._extract_keywords(user_text.lower())
            
            # 최근 10개 캐시와 키워드 매칭
            for i in range(10):
                cache_key = f"llm_keyword:{phone_id}:{i}"
                cached_data = cache.get(cache_key)
                
                if cached_data:
                    cached_keywords = cached_data.get('keywords', [])
                    
                    # 키워드 매칭도 계산 (간단한 Jaccard 유사도)
                    intersection = len(set(keywords) & set(cached_keywords))
                    union = len(set(keywords) | set(cached_keywords))
                    
                    if union > 0:
                        similarity = intersection / union
                        
                        if similarity > 0.6:  # 60% 이상 유사
                            logger.info(f"⚡ 키워드 유사 캐시 히트: {similarity:.2f}")
                            return cached_data['response']
            
            return None
            
        except Exception as e:
            logger.warning(f"키워드 캐시 확인 실패: {e}")
            return None

    def _extract_keywords(self, text: str) -> list:
        """간단한 키워드 추출"""
        # 불용어 제거 및 키워드 추출
        stop_words = {'은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', '의', '로', '으로', '하다', '있다', '되다'}
        words = text.split()
        
        # 2글자 이상의 의미있는 단어만 선택
        keywords = [word for word in words if len(word) >= 2 and word not in stop_words]
        
        return keywords[:5]  # 상위 5개 키워드만


    async def _start_streaming_response(self, phone_id: str, user_text: str) -> Dict[str, Any]:
        """스트리밍 응답 시작"""
        start_time = time.time()
        
        try:
            messages = [
                SystemMessage(content="간결하고 도움이 되는 답변을 해주세요."),
                HumanMessage(content=user_text)
            ]
            
            response_chunks = []
            full_response = ""
            
            # 스트리밍 실행
            async for chunk in self.fast_llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    full_response += chunk.content
                    response_chunks.append(chunk.content)
            
            # 응답 캐싱
            self._cache_response(phone_id, user_text, full_response)
            
            return {
                "content": full_response,
                "source": "streaming",
                "processing_time": time.time() - start_time,
                "chunks": len(response_chunks),
                "is_fast": False
            }
            
        except Exception as e:
            logger.error(f"스트리밍 응답 오류: {e}")
            return {
                "content": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                "source": "error",
                "processing_time": time.time() - start_time,
                "is_fast": False
            }

    async def _generate_accurate_background(self, phone_id: str, user_text: str):
        """백그라운드에서 정확한 응답 생성"""
        try:
            messages = [
                SystemMessage(content="정확하고 상세한 답변을 해주세요."),
                HumanMessage(content=user_text)
            ]
            
            # 정확한 LLM으로 응답 생성
            response = await self.accurate_llm.ainvoke(messages)
            
            if response and response.content:
                # 정확한 응답으로 캐시 업데이트
                exact_cache_key = f"llm_exact:{phone_id}:{hash(user_text)}"
                cache.set(exact_cache_key, response.content, timeout=self.cache_ttl)
                
                logger.info(f"🎯 백그라운드 정확한 응답 생성 완료: {len(response.content)}자")
                
        except Exception as e:
            logger.error(f"백그라운드 응답 생성 오류: {e}")

    def _cache_response(self, phone_id: str, user_text: str, response: str):
        """응답 캐싱 (다중 레벨)"""
        try:
            # 1. 완전 일치 캐시
            exact_cache_key = f"llm_exact:{phone_id}:{hash(user_text)}"
            cache.set(exact_cache_key, response, timeout=self.cache_ttl)
            
            # 2. 키워드 기반 캐시
            keywords = self._extract_keywords(user_text.lower())
            keyword_cache_key = f"llm_keyword:{phone_id}:{hash(user_text) % 10}"
            
            cache.set(keyword_cache_key, {
                'text': user_text,
                'response': response,
                'keywords': keywords,
                'timestamp': time.time()
            }, timeout=self.cache_ttl)
            
            logger.info(f"💾 응답 캐싱 완료: {len(response)}자")
            
        except Exception as e:
            logger.warning(f"캐싱 실패: {e}")

# 전역 인스턴스
optimized_streaming_llm = OptimizedStreamingLLM()

# 기존 인터페이스 호환성을 위한 함수
async def start_chat_optimized(phone_id: str, question: str) -> str:
    """기존 start_chat 함수의 최적화된 버전"""
    try:
        result = await optimized_streaming_llm.get_instant_response(phone_id, question)
        return result.get('content', '응답을 생성할 수 없습니다.')
    except Exception as e:
        logger.error(f"최적화된 채팅 오류: {e}")
        return f"응답 생성 중 오류가 발생했습니다: {str(e)}" 