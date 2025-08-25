"""
🚀 Local LLM Integration System
Ollama + Llama 3.2 1B 로컬 LLM 통합
네트워크 지연 제거 + 초고속 추론
"""
import asyncio
import httpx
import json
import logging
import time
import subprocess
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class LocalModelType(Enum):
    LLAMA_32_1B = "llama3.2:1b"
    LLAMA_32_3B = "llama3.2:3b"
    PHI3_MINI = "phi3:mini"
    QWEN2_1B = "qwen2:1.5b"
    GEMMA2_2B = "gemma2:2b"

@dataclass
class LocalModelConfig:
    model_type: LocalModelType
    name: str
    max_tokens: int
    temperature: float = 0.0
    timeout: float = 1.0
    enabled: bool = True

class OllamaManager:
    """Ollama 로컬 LLM 관리자"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.available_models = []
        self.model_configs = self._get_default_configs()
        self.is_running = False
    
    def _get_default_configs(self) -> List[LocalModelConfig]:
        """기본 모델 설정"""
        return [
            LocalModelConfig(
                model_type=LocalModelType.LLAMA_32_1B,
                name="llama32_1b_ultra_fast",
                max_tokens=50,
                temperature=0.0,
                timeout=0.5
            ),
            LocalModelConfig(
                model_type=LocalModelType.PHI3_MINI,
                name="phi3_mini_balanced",
                max_tokens=80,
                temperature=0.0,
                timeout=1.0
            ),
            LocalModelConfig(
                model_type=LocalModelType.QWEN2_1B,
                name="qwen2_1b_fast",
                max_tokens=60,
                temperature=0.0,
                timeout=0.8
            )
        ]
    
    async def check_ollama_status(self) -> bool:
        """Ollama 서버 상태 확인"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    self.is_running = True
                    data = response.json()
                    self.available_models = [model['name'] for model in data.get('models', [])]
                    logger.info(f"✅ Ollama 실행 중, 사용 가능한 모델: {len(self.available_models)}개")
                    return True
        except Exception as e:
            logger.warning(f"❌ Ollama 서버 연결 실패: {e}")
            self.is_running = False
        
        return False
    
    async def auto_install_models(self) -> bool:
        """필요한 모델 자동 설치"""
        if not self.is_running:
            return False
        
        required_models = [config.model_type.value for config in self.model_configs]
        missing_models = [model for model in required_models if model not in self.available_models]
        
        if not missing_models:
            logger.info("✅ 모든 필요한 모델이 설치되어 있습니다")
            return True
        
        logger.info(f"📥 {len(missing_models)}개 모델 설치 시작: {missing_models}")
        
        for model in missing_models:
            try:
                logger.info(f"📥 {model} 설치 중...")
                
                async with httpx.AsyncClient(timeout=300.0) as client:  # 5분 타임아웃
                    async with client.stream('POST', f"{self.base_url}/api/pull", 
                                           json={"name": model}) as response:
                        if response.status_code == 200:
                            async for chunk in response.aiter_text():
                                if chunk.strip():
                                    try:
                                        status = json.loads(chunk)
                                        if 'status' in status:
                                            logger.info(f"📥 {model}: {status['status']}")
                                    except:
                                        pass
                    
                    logger.info(f"✅ {model} 설치 완료")
                    
            except Exception as e:
                logger.error(f"❌ {model} 설치 실패: {e}")
                return False
        
        # 설치 후 모델 목록 업데이트
        await self.check_ollama_status()
        return True
    
    async def start_ollama_service(self) -> bool:
        """Ollama 서비스 시작 (필요시)"""
        if await self.check_ollama_status():
            return True
        
        try:
            logger.info("🚀 Ollama 서비스 시작 시도...")
            
            # macOS/Linux에서 ollama serve 실행
            process = subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # 서비스 시작 대기 (최대 10초)
            for i in range(10):
                await asyncio.sleep(1)
                if await self.check_ollama_status():
                    logger.info("✅ Ollama 서비스 시작 완료")
                    return True
            
            logger.warning("⏰ Ollama 서비스 시작 타임아웃")
            return False
            
        except FileNotFoundError:
            logger.error("❌ Ollama가 설치되지 않았습니다. https://ollama.ai/install 에서 설치하세요")
            return False
        except Exception as e:
            logger.error(f"❌ Ollama 서비스 시작 실패: {e}")
            return False

class LocalLLMProvider:
    """로컬 LLM 제공자"""
    
    def __init__(self, config: LocalModelConfig, base_url: str = "http://localhost:11434"):
        self.config = config
        self.base_url = base_url
        self.model_name = config.model_type.value
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'average_response_time': 0.0,
            'error_count': 0
        }
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """텍스트 생성"""
        start_time = time.time()
        self.stats['total_calls'] += 1
        
        try:
            # 한국어 최적화 프롬프트
            optimized_prompt = self._optimize_prompt_for_korean(prompt)
            
            timeout = kwargs.get('timeout', self.config.timeout)
            max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": optimized_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": self.config.temperature,
                            "top_k": 10,  # 더 결정적인 답변
                            "top_p": 0.9,
                            "repeat_penalty": 1.1,
                            "stop": ["\\n\\n", "사용자:", "User:", "질문:"]  # 조기 종료
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result.get('response', '').strip()
                    
                    # 후처리
                    processed_text = self._post_process_response(generated_text)
                    
                    processing_time = time.time() - start_time
                    self.stats['successful_calls'] += 1
                    self.stats['average_response_time'] = (
                        self.stats['average_response_time'] * (self.stats['successful_calls'] - 1) + processing_time
                    ) / self.stats['successful_calls']
                    
                    logger.info(f"🚀 {self.config.name} 응답: {processing_time:.3f}초")
                    
                    return {
                        'content': processed_text,
                        'model': self.config.name,
                        'processing_time': processing_time,
                        'success': True,
                        'tokens_generated': len(generated_text.split()),
                        'model_stats': result.get('eval_count', 0)
                    }
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
        except Exception as e:
            self.stats['error_count'] += 1
            processing_time = time.time() - start_time
            
            logger.error(f"❌ {self.config.name} 오류: {e}")
            
            return {
                'content': None,
                'model': self.config.name,
                'error': str(e),
                'success': False,
                'processing_time': processing_time
            }
    
    def _optimize_prompt_for_korean(self, prompt: str) -> str:
        """한국어 응답을 위한 프롬프트 최적화"""
        # 간단하고 직접적인 지시
        optimized = f"""다음 질문에 간단하고 자연스러운 한국어로 답변하세요. 1-2문장으로 답변하세요.

질문: {prompt}

답변:"""
        
        return optimized
    
    def _post_process_response(self, text: str) -> str:
        """응답 후처리"""
        if not text:
            return "네, 알겠습니다!"
        
        # 불필요한 부분 제거
        text = text.strip()
        
        # 영어가 섞여있으면 제거 시도
        lines = text.split('\n')
        korean_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 한국어 비율 체크
            korean_chars = sum(1 for c in line if '\uac00' <= c <= '\ud7af')
            total_chars = len([c for c in line if c.isalpha()])
            
            if total_chars == 0 or korean_chars / total_chars > 0.3:
                korean_lines.append(line)
        
        result = ' '.join(korean_lines) if korean_lines else text
        
        # 최대 길이 제한
        if len(result) > 200:
            sentences = result.split('.')
            result = '.'.join(sentences[:2]) + ('.' if len(sentences) > 2 else '')
        
        return result if result else "네, 말씀해 주세요!"
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보"""
        total_calls = self.stats['total_calls']
        if total_calls == 0:
            return self.stats
        
        return {
            **self.stats,
            'success_rate': self.stats['successful_calls'] / total_calls * 100,
            'error_rate': self.stats['error_count'] / total_calls * 100
        }

class LocalLLMSystem:
    """로컬 LLM 통합 시스템"""
    
    def __init__(self):
        self.ollama_manager = OllamaManager()
        self.providers = []
        self.is_initialized = False
        self.initialization_lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """시스템 초기화"""
        async with self.initialization_lock:
            if self.is_initialized:
                return True
            
            logger.info("🚀 로컬 LLM 시스템 초기화 시작...")
            
            # 1. Ollama 상태 확인 및 시작
            if not await self.ollama_manager.check_ollama_status():
                if not await self.ollama_manager.start_ollama_service():
                    logger.warning("❌ Ollama 서비스를 시작할 수 없습니다")
                    return False
            
            # 2. 필요한 모델 설치
            if not await self.ollama_manager.auto_install_models():
                logger.warning("⚠️ 일부 모델 설치에 실패했습니다")
            
            # 3. 제공자 초기화
            self.providers = []
            for config in self.ollama_manager.model_configs:
                if config.model_type.value in self.ollama_manager.available_models:
                    provider = LocalLLMProvider(config)
                    self.providers.append(provider)
                    logger.info(f"✅ {config.name} 제공자 초기화 완료")
                else:
                    logger.warning(f"⚠️ {config.name} 모델을 사용할 수 없습니다")
            
            if self.providers:
                self.is_initialized = True
                logger.info(f"🎉 로컬 LLM 시스템 초기화 완료: {len(self.providers)}개 제공자")
                return True
            else:
                logger.error("❌ 사용 가능한 로컬 LLM 제공자가 없습니다")
                return False
    
    async def generate_fast(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """가장 빠른 로컬 LLM으로 생성"""
        if not self.is_initialized:
            await self.initialize()
        
        if not self.providers:
            return {
                'content': None,
                'model': 'local_unavailable',
                'error': 'No local LLM providers available',
                'success': False,
                'processing_time': 0.0
            }
        
        # 가장 빠른 제공자 (첫 번째) 사용
        fastest_provider = self.providers[0]
        return await fastest_provider.generate(prompt, **kwargs)
    
    async def generate_parallel_local(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """모든 로컬 LLM을 병렬로 실행하여 가장 빠른 응답 선택"""
        if not self.is_initialized:
            await self.initialize()
        
        if not self.providers:
            return await self.generate_fast(prompt, **kwargs)
        
        logger.info(f"🚀 {len(self.providers)}개 로컬 LLM 병렬 실행")
        
        # 모든 제공자 병렬 실행
        tasks = []
        for provider in self.providers:
            task = asyncio.create_task(
                provider.generate(prompt, **kwargs),
                name=provider.config.name
            )
            tasks.append(task)
        
        try:
            # 첫 번째 성공한 결과 반환
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
                timeout=2.0
            )
            
            # 남은 태스크 취소
            for task in pending:
                task.cancel()
            
            # 성공한 결과 찾기
            for task in done:
                try:
                    result = await task
                    if result['success'] and result.get('content'):
                        logger.info(f"🏆 로컬 LLM 승리: {result['model']}")
                        return result
                except Exception as e:
                    logger.error(f"로컬 LLM 태스크 오류: {e}")
                    continue
            
            # 모든 태스크가 실패한 경우
            return {
                'content': "죄송합니다. 잠시 후 다시 시도해 주세요.",
                'model': 'local_fallback',
                'success': True,
                'processing_time': 0.1,
                'is_fallback': True
            }
            
        except asyncio.TimeoutError:
            logger.warning("⏰ 로컬 LLM 병렬 실행 타임아웃")
            return await self.generate_fast(prompt, **kwargs)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 통계"""
        return {
            'is_initialized': self.is_initialized,
            'ollama_running': self.ollama_manager.is_running,
            'available_models': len(self.ollama_manager.available_models),
            'active_providers': len(self.providers),
            'provider_stats': {
                provider.config.name: provider.get_stats() 
                for provider in self.providers
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        if not self.is_initialized:
            await self.initialize()
        
        results = {
            'ollama_status': await self.ollama_manager.check_ollama_status(),
            'providers': {}
        }
        
        # 각 제공자 테스트
        test_prompt = "안녕하세요"
        for provider in self.providers:
            try:
                start_time = time.time()
                result = await provider.generate(test_prompt, timeout=1.0, max_tokens=10)
                
                results['providers'][provider.config.name] = {
                    'status': 'healthy' if result['success'] else 'error',
                    'response_time': time.time() - start_time,
                    'error': result.get('error')
                }
                
            except Exception as e:
                results['providers'][provider.config.name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results

# 전역 인스턴스
local_llm_system = LocalLLMSystem()