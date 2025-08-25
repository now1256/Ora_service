"""
⚡ 500ms 즉시 응답 시스템
한번 물어본 질문은 500ms 안에 바로 응답
"""
import os
import time
import logging
import hashlib
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from django.core.cache import cache

logger = logging.getLogger(__name__)

# 로컬 메모리 캐시 (가장 빠름)
_local_memory_cache = {}
_vector_response_cache = {}

class Instant500msLLM:
    """⚡ 500ms 즉시 응답 시스템"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # ⚡ 초고속 LLM
        self.ultra_fast_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=self.api_key,
            max_tokens=80,
            timeout=1,
            max_retries=0,
            request_timeout=0.8
        )

    async def get_instant_response(self, phone_id: str, user_text: str) -> str:
        """⚡ 500ms 목표 즉시 응답"""
        start_time = time.time()
        
        # 1. 🚀 로컬 메모리 캐시 (0.001초)
        local_cache_key = f"{phone_id}:{hash(user_text.lower().strip())}"
        if local_cache_key in _local_memory_cache:
            elapsed = time.time() - start_time
            logger.info(f"🚀 로컬 캐시: {elapsed*1000:.1f}ms")
            return _local_memory_cache[local_cache_key]

        # 2. 💾 Redis 캐시 (10ms)
        redis_cache_key = f"instant:{phone_id}:{hashlib.md5(user_text.encode()).hexdigest()}"
        cached = cache.get(redis_cache_key)
        if cached:
            # 로컬 캐시에도 저장 (다음번 더 빠르게)
            _local_memory_cache[local_cache_key] = cached
            elapsed = time.time() - start_time
            logger.info(f"💾 Redis 캐시: {elapsed*1000:.1f}ms")
            return cached

        # 3. 🔍 벡터 DB 빠른 검색 시도 (100ms 제한)
        vector_response = self._try_vector_search_fast(phone_id, user_text, max_time=0.1)
        if vector_response:
            # 모든 캐시에 저장
            self._save_to_all_caches(local_cache_key, redis_cache_key, vector_response)
            elapsed = time.time() - start_time
            logger.info(f"🔍 벡터 DB: {elapsed*1000:.1f}ms")
            return vector_response

        # 4. 🤖 초고속 LLM 생성 (마지막 수단)
        try:
            messages = [
                SystemMessage(content="1-2문장으로 간결하게 답변하세요."),
                HumanMessage(content=user_text)
            ]
            
            response = await self.ultra_fast_llm.ainvoke(messages)
            result = response.content if response and response.content else "네, 알겠습니다!"
            
            # 모든 캐시에 저장
            self._save_to_all_caches(local_cache_key, redis_cache_key, result)
            
            elapsed = time.time() - start_time
            logger.info(f"🤖 새 생성: {elapsed*1000:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"초고속 LLM 오류: {e}")
            return "네, 무엇을 도와드릴까요?"

    def _try_vector_search_fast(self, phone_id: str, user_text: str, max_time: float) -> Optional[str]:
        """🔍 100ms 제한 벡터 DB 검색"""
        start = time.time()
        
        try:
            # 벡터 검색 임포트는 여기서 (에러 방지)
            # from ..weaviate.weaviate_client import weaviate_client
            # import weaviate.classes as wvc
            
            if not weaviate_client or not weaviate_client.is_ready():
                return None
            
            # 시간 제한 확인
            if time.time() - start > max_time:
                return None
                
            conversations = weaviate_client.collections.get("Conversations")
            
            # 초고속 검색 (1개만, 높은 유사도)
            search_results = conversations.query.near_text(
                query=user_text,
                limit=1,
                distance=0.1,  # 매우 높은 유사도 (0.9 이상)
                where=wvc.query.Filter.by_property("phone_id").equal(phone_id),
                return_metadata=['distance'],
                return_properties=['ai_response']
            )
            
            # 시간 제한 재확인
            if time.time() - start > max_time:
                return None
            
            if search_results.objects:
                best_match = search_results.objects[0]
                if hasattr(best_match, 'metadata') and best_match.metadata.distance <= 0.1:
                    ai_response = best_match.properties.get('ai_response')
                    if ai_response and len(ai_response.strip()) > 0:
                        return ai_response
                        
            return None
            
        except Exception as e:
            logger.warning(f"벡터 DB 검색 스킵 (오류): {e}")
            return None

    def _save_to_all_caches(self, local_key: str, redis_key: str, response: str):
        """모든 캐시에 저장"""
        try:
            # 로컬 메모리 캐시 (가장 빠름)
            _local_memory_cache[local_key] = response
            
            # 로컬 캐시 크기 제한 (1000개)
            if len(_local_memory_cache) > 1000:
                # 가장 오래된 500개 제거
                keys_to_remove = list(_local_memory_cache.keys())[:500]
                for key in keys_to_remove:
                    del _local_memory_cache[key]
            
            # Redis 캐시
            cache.set(redis_key, response, timeout=1800)  # 30분
            
        except Exception as e:
            logger.error(f"캐시 저장 오류: {e}")


# 전역 인스턴스
instant_500ms_llm = Instant500msLLM()

# 동기 래퍼 함수
def start_chat_instant_500ms(phone_id: str, question: str) -> str:
    """500ms 즉시 응답 동기 버전"""
    import asyncio
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                instant_500ms_llm.get_instant_response(phone_id, question)
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"500ms 시스템 오류: {e}")
        # 안전한 fallback
        return "네, 말씀해 주세요!" 