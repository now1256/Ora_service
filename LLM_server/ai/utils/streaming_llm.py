"""
🚀 현업 레벨 스트리밍 LLM 서비스
실시간 스트리밍으로 체감 속도 극대화
"""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from django.core.cache import cache
import logging
import os

logger = logging.getLogger(__name__)

class StreamingLLMService:
    """🚀 현업용 스트리밍 LLM 서비스"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.streaming_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=self.api_key,
            streaming=True,  # 스트리밍 활성화
            max_tokens=200,
            timeout=8,
            max_retries=1
        )
        
        # 유사 질문 캐시를 위한 임베딩 모델
        try:
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
        except Exception as e:
            logger.warning(f"임베딩 모델 로드 실패: {e}")
            self.embeddings = None

    async def get_streaming_response(
        self, 
        phone_id: str, 
        user_text: str,
        use_cache: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """🚀 스트리밍 응답 생성"""
        
        start_time = time.time()
        
        # 1. 완전 일치 캐시 확인
        if use_cache:
            cache_key = f"llm_response:{phone_id}:{hash(user_text)}"
            cached_response = cache.get(cache_key)
            
            if cached_response:
                logger.info(f"⚡ 캐시 히트: {time.time() - start_time:.3f}초")
                yield {
                    "type": "cached_response",
                    "content": cached_response,
                    "is_final": True,
                    "processing_time": time.time() - start_time,
                    "source": "cache"
                }
                return

        # 2. 유사 질문 캐시 확인
        if use_cache and self.embeddings:
            similar_response = await self._check_similar_cache(phone_id, user_text)
            if similar_response:
                logger.info(f"⚡ 유사 캐시 히트: {time.time() - start_time:.3f}초")
                yield {
                    "type": "similar_response",
                    "content": similar_response,
                    "is_final": True,
                    "processing_time": time.time() - start_time,
                    "source": "similar_cache"
                }
                return

        # 3. 빠른 시작 응답
        yield {
            "type": "start",
            "content": "",
            "is_final": False,
            "processing_time": time.time() - start_time,
            "source": "streaming"
        }

        # 4. 스트리밍 LLM 응답
        try:
            messages = [
                SystemMessage(content="당신은 도움이 되는 AI 어시스턴트입니다. 간결하고 정확하게 답변해주세요."),
                HumanMessage(content=f"[세션: {phone_id}] {user_text}")
            ]
            
            full_response = ""
            chunk_count = 0
            
            # 🚀 스트리밍 실행
            async for chunk in self.streaming_llm.astream(messages):
                chunk_count += 1
                
                if hasattr(chunk, 'content') and chunk.content:
                    full_response += chunk.content
                    
                    yield {
                        "type": "chunk",
                        "content": chunk.content,
                        "full_content": full_response,
                        "is_final": False,
                        "chunk_index": chunk_count,
                        "processing_time": time.time() - start_time,
                        "source": "streaming"
                    }

            # 5. 최종 응답 및 캐싱
            total_time = time.time() - start_time
            
            if full_response:
                # 응답 캐싱 (5분)
                cache_key = f"llm_response:{phone_id}:{hash(user_text)}"
                cache.set(cache_key, full_response, timeout=300)
                
                # 유사 검색을 위한 임베딩 캐싱
                if self.embeddings:
                    await self._cache_for_similarity(phone_id, user_text, full_response)

            yield {
                "type": "final",
                "content": full_response,
                "is_final": True,
                "total_chunks": chunk_count,
                "processing_time": total_time,
                "source": "streaming"
            }
            
            logger.info(f"🚀 스트리밍 완료: {chunk_count}청크, {total_time:.3f}초")

        except Exception as e:
            logger.error(f"❌ 스트리밍 오류: {e}")
            yield {
                "type": "error",
                "content": f"응답 생성 중 오류가 발생했습니다: {str(e)}",
                "is_final": True,
                "processing_time": time.time() - start_time,
                "source": "error"
            }

    async def _check_similar_cache(self, phone_id: str, user_text: str) -> Optional[str]:
        """유사 질문 캐시 확인"""
        try:
            # 현재 질문의 임베딩 생성
            current_embedding = await asyncio.to_thread(
                self.embeddings.embed_query, user_text
            )
            
            # 캐시된 질문들과 유사도 비교
            cache_pattern = f"llm_embedding:{phone_id}:*"
            # Redis 패턴 검색 (실제 구현시 Redis 사용)
            
            # 간단한 구현: 최근 5개 질문과 비교
            for i in range(5):
                cached_key = f"llm_embedding:{phone_id}:{i}"
                cached_data = cache.get(cached_key)
                
                if cached_data:
                    similarity = self._cosine_similarity(
                        current_embedding, 
                        cached_data['embedding']
                    )
                    
                    # 85% 이상 유사하면 캐시된 응답 사용
                    if similarity > 0.85:
                        logger.info(f"⚡ 유사 질문 발견: {similarity:.3f}")
                        return cached_data['response']
            
            return None
            
        except Exception as e:
            logger.warning(f"유사 캐시 확인 실패: {e}")
            return None

    async def _cache_for_similarity(self, phone_id: str, user_text: str, response: str):
        """유사 검색을 위한 임베딩 캐싱"""
        try:
            embedding = await asyncio.to_thread(
                self.embeddings.embed_query, user_text
            )
            
            # 순환 캐싱 (최대 5개)
            import random
            cache_index = random.randint(0, 4)
            cache_key = f"llm_embedding:{phone_id}:{cache_index}"
            
            cache.set(cache_key, {
                'text': user_text,
                'response': response,
                'embedding': embedding,
                'timestamp': time.time()
            }, timeout=1800)  # 30분
            
        except Exception as e:
            logger.warning(f"유사 캐싱 실패: {e}")

    def _cosine_similarity(self, vec1, vec2):
        """코사인 유사도 계산"""
        import numpy as np
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# 싱글톤 인스턴스
streaming_llm_service = StreamingLLMService() 