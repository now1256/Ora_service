"""
⚡ ULTRA 초고속 LLM - 도구 없는 단순 LLM (0.3초 목표)
현업에서 극한 속도가 필요할 때 사용하는 방식
"""
import os
import time
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from django.core.cache import cache

logger = logging.getLogger(__name__)

class UltraFastLLM:
    """⚡ 도구 없는 초고속 LLM"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

        # ⚡ 완전한 문장 보장 + 초고속 LLM
        self.ultra_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=self.api_key,
            max_tokens=100,       # 완전한 문장 보장 (15 → 100자)
            timeout=2,            # 타임아웃 약간 증가
            max_retries=0,        # 재시도 없음
            request_timeout=1.5   # 안정성 확보
        )

    async def get_ultra_fast_response(self, phone_id: str, user_text: str) -> str:
        """⚡ 0.3초 목표 초고속 응답"""
        start_time = time.time()

        # 1. 캐시 확인
        cache_key = f"ultra_llm:{hash(user_text)}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"⚡ 캐시 히트: {time.time() - start_time:.3f}초")
            return cached

        # 2. 도구 없는 단순 LLM 호출
        try:
            messages = [
                SystemMessage(content="1문장만 답변"),
                HumanMessage(content=user_text)
            ]

            response = await self.ultra_llm.ainvoke(messages)
            result = response.content if response and response.content else "네!"

            # 캐싱
            cache.set(cache_key, result, timeout=300)

            elapsed = time.time() - start_time
            logger.info(f"⚡ Ultra LLM: {elapsed:.3f}초")
            return result

        except Exception as e:
            logger.error(f"Ultra LLM 오류: {e}")
            return "네, 알겠습니다!"

# 전역 인스턴스
ultra_fast_llm = UltraFastLLM()

# 동기 래퍼 함수
def start_chat_ultra_fast(phone_id: str, question: str) -> str:
    """동기 버전 ultra fast LLM"""
    import asyncio

    try:
        # 이벤트 루프 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                ultra_fast_llm.get_ultra_fast_response(phone_id, question)
            )
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Ultra fast 오류: {e}")
        return "네!"
