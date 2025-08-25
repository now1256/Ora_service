"""
🚀 Parallel LLM System - Multi-Model First-Win Architecture
여러 LLM을 동시에 호출하여 가장 빠른 응답 선택
"""
import asyncio
import httpx
import time
import logging
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class ModelPriority(Enum):
    ULTRA_FAST = 1
    BALANCED = 2  
    ACCURATE = 3
    LOCAL = 4

@dataclass
class ModelConfig:
    name: str
    model_id: str
    max_tokens: int
    timeout: float
    priority: ModelPriority
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True

class LLMProvider:
    """개별 LLM 제공자 추상 클래스"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """클라이언트 초기화"""
        pass
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """텍스트 생성"""
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI GPT 제공자"""
    
    def _initialize_client(self):
        self.client = ChatOpenAI(
            model=self.config.model_id,
            api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
            max_tokens=self.config.max_tokens,
            temperature=0,
            timeout=self.config.timeout,
            max_retries=0,
            streaming=False
        )
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        try:
            start_time = time.time()
            
            # 메시지 변환
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                else:
                    langchain_messages.append(HumanMessage(content=msg["content"]))
            
            response = await self.client.ainvoke(langchain_messages)
            
            return {
                'content': response.content,
                'model': self.config.name,
                'processing_time': time.time() - start_time,
                'success': True,
                'priority': self.config.priority.value
            }
            
        except Exception as e:
            logger.error(f"{self.config.name} 오류: {e}")
            return {
                'content': None,
                'model': self.config.name,
                'error': str(e),
                'success': False,
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0
            }

class OllamaProvider(LLMProvider):
    """Ollama 로컬 LLM 제공자"""
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        try:
            start_time = time.time()
            
            # 마지막 사용자 메시지만 사용 (속도 최적화)
            user_message = ""
            for msg in reversed(messages):
                if msg["role"] == "user":
                    user_message = msg["content"]
                    break
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.model_id,
                        "prompt": user_message,
                        "stream": False,
                        "options": {
                            "num_predict": self.config.max_tokens,
                            "temperature": 0
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        'content': result.get('response', ''),
                        'model': self.config.name,
                        'processing_time': time.time() - start_time,
                        'success': True,
                        'priority': self.config.priority.value
                    }
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.warning(f"{self.config.name} 오류: {e}")
            return {
                'content': None,
                'model': self.config.name,
                'error': str(e),
                'success': False,
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0
            }

class ClaudeProvider(LLMProvider):
    """Anthropic Claude 제공자 (향후 확장용)"""
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        # Claude API 구현 (현재는 스킵)
        return {
            'content': None,
            'model': self.config.name,
            'error': 'Claude provider not implemented',
            'success': False,
            'processing_time': 0
        }

class ParallelLLMSystem:
    """병렬 LLM 호출 시스템"""
    
    def __init__(self):
        self.providers = []
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'model_wins': {},
            'average_response_time': 0.0
        }
        self._initialize_providers()
    
    def _initialize_providers(self):
        """LLM 제공자들 초기화"""
        
        # GPT-3.5-turbo (초고속)
        gpt35_config = ModelConfig(
            name="gpt35_turbo",
            model_id="gpt-3.5-turbo",
            max_tokens=80,
            timeout=2.0,
            priority=ModelPriority.ULTRA_FAST,
            enabled=bool(os.getenv("OPENAI_API_KEY"))
        )
        if gpt35_config.enabled:
            self.providers.append(OpenAIProvider(gpt35_config))
        
        # GPT-4o-mini (균형)
        gpt4mini_config = ModelConfig(
            name="gpt4o_mini",
            model_id="gpt-4o-mini",
            max_tokens=120,
            timeout=3.0,
            priority=ModelPriority.BALANCED,
            enabled=bool(os.getenv("OPENAI_API_KEY"))
        )
        if gpt4mini_config.enabled:
            self.providers.append(OpenAIProvider(gpt4mini_config))
        
        # Ollama Llama 3.2 (로컬)
        ollama_config = ModelConfig(
            name="llama32_local",
            model_id="llama3.2:1b",
            max_tokens=60,
            timeout=1.0,
            priority=ModelPriority.LOCAL,
            base_url="http://localhost:11434",
            enabled=True  # 항상 시도 (실패해도 OK)
        )
        self.providers.append(OllamaProvider(ollama_config))
        
        logger.info(f"🚀 {len(self.providers)}개 LLM 제공자 초기화 완료")
    
    async def generate_parallel(self, messages: List[Dict[str, str]], 
                              strategy: str = "first_win",
                              quality_check: bool = True) -> Dict[str, Any]:
        """병렬 LLM 호출"""
        
        if not self.providers:
            return {
                'content': "죄송합니다. 사용 가능한 LLM이 없습니다.",
                'model': 'fallback',
                'success': False,
                'error': 'No providers available'
            }
        
        start_time = time.time()
        self.stats['total_calls'] += 1
        
        # 활성화된 제공자들로 병렬 호출
        tasks = []
        for provider in self.providers:
            if provider.config.enabled:
                task = asyncio.create_task(
                    provider.generate(messages),
                    name=provider.config.name
                )
                tasks.append((task, provider))
        
        if not tasks:
            return {
                'content': "죄송합니다. 활성화된 LLM이 없습니다.",
                'model': 'fallback',
                'success': False
            }
        
        logger.info(f"🚀 {len(tasks)}개 LLM 병렬 호출 시작")
        
        if strategy == "first_win":
            return await self._first_win_strategy(tasks, start_time, quality_check)
        elif strategy == "race_with_timeout":
            return await self._race_with_timeout_strategy(tasks, start_time, 1.0)
        else:
            return await self._best_quality_strategy(tasks, start_time)
    
    async def _first_win_strategy(self, tasks: List[Tuple], start_time: float, 
                                quality_check: bool) -> Dict[str, Any]:
        """첫 번째 성공한 응답 선택"""
        
        completed_tasks = []
        pending_tasks = [task for task, _ in tasks]
        
        try:
            while pending_tasks:
                done, pending_tasks = await asyncio.wait(
                    pending_tasks, 
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=0.5
                )
                
                for task in done:
                    result = await task
                    completed_tasks.append(result)
                    
                    if result['success'] and result.get('content'):
                        # 품질 체크
                        if not quality_check or self._is_quality_response(result['content']):
                            # 승자 기록
                            model_name = result['model']
                            self.stats['model_wins'][model_name] = self.stats['model_wins'].get(model_name, 0) + 1
                            self.stats['successful_calls'] += 1
                            
                            # 남은 태스크들 취소
                            for pending_task in pending_tasks:
                                pending_task.cancel()
                            
                            total_time = time.time() - start_time
                            logger.info(f"🏆 {model_name} 승리! 총 시간: {total_time:.3f}초")
                            
                            return {
                                **result,
                                'total_processing_time': total_time,
                                'completed_models': len(completed_tasks)
                            }
                
                # 타임아웃 체크
                if time.time() - start_time > 3.0:
                    logger.warning("⏰ 모든 LLM 타임아웃")
                    break
            
            # 모든 태스크 완료 후에도 성공한 응답이 없는 경우
            successful_results = [r for r in completed_tasks if r['success']]
            if successful_results:
                # 우선순위 기준으로 선택
                best_result = min(successful_results, key=lambda x: x['priority'])
                return {
                    **best_result,
                    'total_processing_time': time.time() - start_time,
                    'completed_models': len(completed_tasks)
                }
            
        except Exception as e:
            logger.error(f"병렬 처리 오류: {e}")
        
        # 모든 실패 시 폴백
        return await self._get_fallback_response(start_time)
    
    async def _race_with_timeout_strategy(self, tasks: List[Tuple], start_time: float, 
                                        timeout: float) -> Dict[str, Any]:
        """타임아웃 기반 레이스"""
        try:
            done, pending = await asyncio.wait(
                [task for task, _ in tasks],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 남은 태스크 취소
            for task in pending:
                task.cancel()
            
            # 완료된 태스크 중 가장 좋은 결과 선택
            results = []
            for task in done:
                try:
                    result = await task
                    if result['success']:
                        results.append(result)
                except:
                    pass
            
            if results:
                best_result = min(results, key=lambda x: x['priority'])
                return {
                    **best_result,
                    'total_processing_time': time.time() - start_time
                }
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ {timeout}초 타임아웃")
        
        return await self._get_fallback_response(start_time)
    
    def _is_quality_response(self, content: str) -> bool:
        """응답 품질 체크"""
        if not content or len(content.strip()) < 2:
            return False
        
        # 에러 메시지 패턴 체크
        error_patterns = ['error', '오류', 'sorry', '죄송', 'cannot', '할 수 없']
        content_lower = content.lower()
        
        # 에러 패턴이 너무 많으면 품질이 낮음
        error_count = sum(1 for pattern in error_patterns if pattern in content_lower)
        
        return error_count <= 1 and len(content.strip()) >= 10
    
    async def _get_fallback_response(self, start_time: float) -> Dict[str, Any]:
        """폴백 응답"""
        fallback_responses = [
            "네, 말씀해 주세요!",
            "알겠습니다. 더 도움이 필요하시면 말씀해 주세요.",
            "네, 무엇을 도와드릴까요?",
            "좋습니다!"
        ]
        
        import random
        response = random.choice(fallback_responses)
        
        return {
            'content': response,
            'model': 'fallback',
            'success': True,
            'total_processing_time': time.time() - start_time,
            'is_fallback': True
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """시스템 통계"""
        total_calls = self.stats['total_calls']
        if total_calls == 0:
            return self.stats
        
        return {
            **self.stats,
            'success_rate': self.stats['successful_calls'] / total_calls * 100,
            'provider_count': len(self.providers),
            'enabled_providers': len([p for p in self.providers if p.config.enabled])
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """시스템 상태 체크"""
        results = {}
        
        test_messages = [{"role": "user", "content": "안녕하세요"}]
        
        for provider in self.providers:
            if not provider.config.enabled:
                results[provider.config.name] = {'status': 'disabled'}
                continue
                
            try:
                start_time = time.time()
                result = await provider.generate(test_messages)
                
                results[provider.config.name] = {
                    'status': 'healthy' if result['success'] else 'error',
                    'response_time': time.time() - start_time,
                    'error': result.get('error')
                }
                
            except Exception as e:
                results[provider.config.name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results

# 전역 인스턴스
parallel_llm = ParallelLLMSystem()