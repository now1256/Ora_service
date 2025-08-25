"""
🎯 커서 AI - 벡터 DB 우선 검색 시스템
"Search First, Generate if Absent" 원칙 구현
"""
import os
import time
import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from django.core.cache import cache

# Weaviate 직접 접근
# from ..weaviate.weaviate_client import weaviate_client
# import weaviate.classes as wvc

logger = logging.getLogger(__name__)

class VectorFirstLLM:
    """🎯 벡터 DB 우선 검색 LLM 시스템"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.weaviate_client = weaviate_client
        
        # ⚡ 빠른 LLM (fallback용)
        self.fast_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=self.api_key,
            max_tokens=100,
            timeout=2,
            max_retries=0,
            request_timeout=1.5
        )

    async def get_response_vector_first(self, phone_id: str, user_text: str) -> str:
        """🎯 벡터 DB 우선 검색 → 즉시 응답"""
        start_time = time.time()
        
        # 1. 🔍 벡터 DB 우선 검색 (핵심!)
        vector_response = self._search_vector_db_fast(phone_id, user_text)
        if vector_response:
            elapsed = time.time() - start_time
            logger.info(f"🎯 벡터 DB 히트: {elapsed:.3f}초")
            return vector_response

        # 2. 💾 LLM 캐시 확인
        cache_key = f"llm_cache:{hash(user_text)}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"💾 캐시 히트: {time.time() - start_time:.3f}초")
            return cached

        # 3. 🤖 새로운 LLM 생성 (마지막 수단)
        try:
            messages = [
                SystemMessage(content="간결하게 1-2문장으로 답변하세요."),
                HumanMessage(content=user_text)
            ]
            
            response = await self.fast_llm.ainvoke(messages)
            result = response.content if response and response.content else "네, 알겠습니다!"
            
            # 캐싱 및 벡터 DB 저장
            cache.set(cache_key, result, timeout=300)
            self._save_to_vector_db_async(phone_id, user_text, result)
            
            elapsed = time.time() - start_time
            logger.info(f"🤖 새 생성: {elapsed:.3f}초")
            return result
            
        except Exception as e:
            logger.error(f"LLM 생성 오류: {e}")
            return "죄송합니다. 다시 말씀해 주세요."

    def _search_vector_db_fast(self, phone_id: str, user_text: str) -> Optional[str]:
        """🔍 벡터 DB 초고속 검색"""
        try:
            if not self.weaviate_client or not self.weaviate_client.is_ready():
                return None
                
            # 🎯 폰 ID별 대화 컬렉션 검색
            conversations = self.weaviate_client.collections.get("Conversations")
            
            # 🎯 초고속 유사도 검색 (임계값 0.85 이상)
            search_results = conversations.query.near_text(
                query=user_text,
                limit=1,  # 가장 유사한 1개만 (속도 최적화)
                distance=0.15,  # 매우 높은 유사도만 (0.85 이상)
                where=wvc.query.Filter.by_property("phone_id").equal(phone_id),
                return_metadata=['distance'],  # 메타데이터 최소화
                return_properties=['ai_response']  # 필요한 속성만 반환
            )
            
            if search_results.objects:
                # 가장 유사한 결과의 답변 반환
                best_match = search_results.objects[0]
                
                # 유사도 점수 확인 (거리가 0.15 이하 = 유사도 0.85 이상)
                if hasattr(best_match, 'metadata') and best_match.metadata.distance <= 0.15:
                    ai_response = best_match.properties.get('ai_response')
                    if ai_response and len(ai_response.strip()) > 0:
                        logger.info(f"🎯 벡터 DB 매치 발견: 유사도 {1-best_match.metadata.distance:.3f}")
                        return ai_response
                        
            return None
            
        except Exception as e:
            logger.error(f"벡터 DB 검색 오류: {e}")
            return None

    def _save_to_vector_db_async(self, phone_id: str, user_text: str, ai_response: str):
        """📝 벡터 DB에 새 대화 비동기 저장"""
        try:
            import threading
            
            def save_worker():
                try:
                    if not self.weaviate_client or not self.weaviate_client.is_ready():
                        return
                        
                    conversations = self.weaviate_client.collections.get("Conversations")
                    
                    conversations.data.insert({
                        "phone_id": phone_id,
                        "user_input": user_text,
                        "ai_response": ai_response,
                        "timestamp": time.time(),
                        "session_type": "vector_first"
                    })
                    
                    logger.info("📝 벡터 DB 저장 완료 (백그라운드)")
                    
                except Exception as e:
                    logger.error(f"벡터 DB 저장 오류: {e}")
            
            # 백그라운드 스레드로 저장
            thread = threading.Thread(target=save_worker)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"벡터 DB 비동기 저장 설정 오류: {e}")


# 전역 인스턴스
vector_first_llm = VectorFirstLLM()

# 동기 래퍼 함수
def start_chat_vector_first(phone_id: str, question: str) -> str:
    """벡터 DB 우선 검색 동기 버전"""
    import asyncio
    
    try:
        # 이벤트 루프 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                vector_first_llm.get_response_vector_first(phone_id, question)
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"벡터 우선 검색 오류: {e}")
        return "죄송합니다. 잠시 후 다시 시도해 주세요." 