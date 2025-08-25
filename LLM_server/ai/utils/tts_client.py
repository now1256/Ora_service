# ai/utils/tts_client.py
"""
최적화된 TTS 클라이언트 모듈
- 연결 풀링으로 성능 최적화
- 비동기/동기 전송 지원
- Fire-and-Forget 모드 지원
"""

import asyncio
import aiohttp
import time
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings

logger = logging.getLogger(__name__)

class TTSClient:
    """최적화된 TTS 클라이언트 - 싱글톤 패턴"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.tts_server_url = getattr(settings, 'TTS_SERVER_URL', 'http://tts_server:5002')
        self.tts_url = f"{self.tts_server_url}/api/convert-tts/"
        
        # 동기 세션 설정 (연결 풀링)
        self.sync_session = None
        self.async_session = None
        self.setup_sync_session()
        
        # 성능 통계
        self.stats = {
            "total_requests": 0,
            "total_time": 0,
            "avg_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "success_count": 0,
            "error_count": 0
        }
        
        self._initialized = True
        logger.info(f"🚀 TTS 클라이언트 초기화 완료: {self.tts_url}")
    
    def setup_sync_session(self):
        """동기 세션 설정 - 연결 풀링으로 성능 최적화"""
        self.sync_session = requests.Session()
        
        # 연결 풀 및 재시도 설정
        retry_strategy = Retry(
            total=3,                    # 최대 재시도 횟수
            backoff_factor=0.1,         # 재시도 간격
            status_forcelist=[500, 502, 503, 504],  # 재시도할 HTTP 상태 코드
            allowed_methods=["POST"]     # POST 요청도 재시도
        )
        
        adapter = HTTPAdapter(
            pool_connections=20,        # 연결 풀 크기
            pool_maxsize=50,           # 최대 연결 수
            max_retries=retry_strategy
        )
        
        self.sync_session.mount('http://', adapter)
        self.sync_session.mount('https://', adapter)
        
        # 기본 헤더 설정 (Keep-Alive 포함)
        self.sync_session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Connection': 'keep-alive',
            'User-Agent': 'Groq-LLM-Client/1.0'
        })
        
        logger.info("✅ TTS 동기 세션 연결 풀 설정 완료")
    
    async def setup_async_session(self):
        """비동기 세션 설정"""
        if self.async_session is None:
            connector = aiohttp.TCPConnector(
                limit=100,              # 전체 연결 수 제한
                limit_per_host=30,      # 호스트당 연결 수 제한
                keepalive_timeout=60,   # Keep-alive 타임아웃
                enable_cleanup_closed=True,
                use_dns_cache=True,     # DNS 캐시 사용
                ttl_dns_cache=300       # DNS 캐시 TTL (5분)
            )
            
            timeout = aiohttp.ClientTimeout(
                total=15,               # 전체 타임아웃
                connect=3,              # 연결 타임아웃
                sock_read=10            # 읽기 타임아웃
            )
            
            self.async_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'Groq-LLM-AsyncClient/1.0'
                }
            )
            
            logger.info("✅ TTS 비동기 세션 설정 완료")
    
    def send_sync_optimized(self, tts_message: Dict[str, Any], use_websocket: bool = True) -> Dict[str, Any]:
        """최적화된 동기 TTS 전송 (연결 풀링 사용)"""
        start_time = time.time()
        
        try:
            # WebSocket 사용 옵션 추가
            tts_message['use_websocket'] = use_websocket
            tts_message['fire_and_forget'] = True  # 기본적으로 Fire-and-forget 모드
            
            logger.debug(f"📤 [TTS 풀링] 전송 시작: {tts_message.get('requestId', 'unknown')} (WebSocket: {use_websocket})")
            
            # 연결 풀을 사용한 동기 전송
            response = self.sync_session.post(
                self.tts_url,
                json=tts_message,
                timeout=(3, 12),        # (연결, 읽기) 타임아웃
                stream=False           # 스트리밍 비활성화
            )
            
            elapsed_time = time.time() - start_time
            
            # 응답 검증
            response.raise_for_status()
            
            # 성능 통계 업데이트
            self.update_stats(elapsed_time, success=True)
            
            logger.info(f"✅ [TTS 풀링] 성공: {elapsed_time:.3f}초 (상태: {response.status_code})")
            
            return {
                'success': True,
                'status_code': response.status_code,
                'data': response.json() if response.content else None,
                'response_time': elapsed_time,
                'method': 'sync_pooled',
                'llm_provider': 'Groq',
                'stats': self.get_current_stats()
            }
            
        except requests.exceptions.ConnectionError as e:
            elapsed_time = time.time() - start_time
            self.update_stats(elapsed_time, success=False)
            logger.error(f"❌ [TTS 풀링] 연결 오류: {e} ({elapsed_time:.3f}초)")
            
            return {
                'success': False,
                'error': f'TTS 서버 연결 실패: {str(e)[:100]}',
                'error_type': 'connection_error',
                'response_time': elapsed_time,
                'method': 'sync_pooled'
            }
            
        except requests.exceptions.Timeout as e:
            elapsed_time = time.time() - start_time
            self.update_stats(elapsed_time, success=False)
            logger.error(f"⏰ [TTS 풀링] 타임아웃: {e} ({elapsed_time:.3f}초)")
            
            return {
                'success': False,
                'error': f'TTS 서버 타임아웃: {str(e)[:100]}',
                'error_type': 'timeout',
                'response_time': elapsed_time,
                'method': 'sync_pooled'
            }
            
        except requests.exceptions.HTTPError as e:
            elapsed_time = time.time() - start_time
            self.update_stats(elapsed_time, success=False)
            logger.error(f"🚫 [TTS 풀링] HTTP 오류: {e} ({elapsed_time:.3f}초)")
            
            return {
                'success': False,
                'error': f'TTS 서버 HTTP 오류: {str(e)[:100]}',
                'error_type': 'http_error',
                'response_time': elapsed_time,
                'method': 'sync_pooled',
                'status_code': getattr(e.response, 'status_code', None)
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.update_stats(elapsed_time, success=False)
            logger.error(f"💥 [TTS 풀링] 예상치 못한 오류: {e} ({elapsed_time:.3f}초)")
            
            return {
                'success': False,
                'error': f'TTS 전송 오류: {str(e)[:100]}',
                'error_type': 'unknown',
                'response_time': elapsed_time,
                'method': 'sync_pooled'
            }
    
    async def send_async(self, tts_message: Dict[str, Any], use_websocket: bool = True) -> Dict[str, Any]:
        """비동기 TTS 전송"""
        await self.setup_async_session()
        start_time = time.time()
        
        try:
            # WebSocket 사용 옵션 추가
            tts_message['use_websocket'] = use_websocket
            tts_message['fire_and_forget'] = True  # 기본적으로 Fire-and-forget 모드
            
            logger.debug(f"📤 [TTS 비동기] 전송 시작: {tts_message.get('requestId', 'unknown')} (WebSocket: {use_websocket})")
            
            async with self.async_session.post(
                self.tts_url,
                json=tts_message
            ) as response:
                elapsed_time = time.time() - start_time
                
                response.raise_for_status()
                data = await response.json() if response.content_length else None
                
                self.update_stats(elapsed_time, success=True)
                
                logger.info(f"✅ [TTS 비동기] 성공: {elapsed_time:.3f}초 (상태: {response.status})")
                
                return {
                    'success': True,
                    'status_code': response.status,
                    'data': data,
                    'response_time': elapsed_time,
                    'method': 'async',
                    'llm_provider': 'Groq',
                    'stats': self.get_current_stats()
                }
                
        except aiohttp.ClientConnectorError as e:
            elapsed_time = time.time() - start_time
            self.update_stats(elapsed_time, success=False)
            logger.error(f"❌ [TTS 비동기] 연결 오류: {e} ({elapsed_time:.3f}초)")
            
            return {
                'success': False,
                'error': f'TTS 서버 연결 실패: {str(e)[:100]}',
                'error_type': 'connection_error',
                'response_time': elapsed_time,
                'method': 'async'
            }
            
        except asyncio.TimeoutError as e:
            elapsed_time = time.time() - start_time
            self.update_stats(elapsed_time, success=False)
            logger.error(f"⏰ [TTS 비동기] 타임아웃: {e} ({elapsed_time:.3f}초)")
            
            return {
                'success': False,
                'error': f'TTS 서버 타임아웃: {str(e)[:100]}',
                'error_type': 'timeout',
                'response_time': elapsed_time,
                'method': 'async'
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.update_stats(elapsed_time, success=False)
            logger.error(f"💥 [TTS 비동기] 오류: {e} ({elapsed_time:.3f}초)")
            
            return {
                'success': False,
                'error': f'TTS 전송 오류: {str(e)[:100]}',
                'error_type': 'unknown',
                'response_time': elapsed_time,
                'method': 'async'
            }
    
    def send_fire_and_forget(self, tts_message: Dict[str, Any], use_websocket: bool = True) -> Dict[str, Any]:
        """Fire-and-Forget 방식 - 가장 빠름 (응답 대기 안함)"""
        def _send_in_background():
            try:
                # WebSocket 사용 옵션 추가
                tts_message['use_websocket'] = use_websocket
                tts_message['fire_and_forget'] = True
                
                start_time = time.time()
                response = self.sync_session.post(
                    self.tts_url,
                    json=tts_message,
                    timeout=(2, 8),  # 더 짧은 타임아웃
                    stream=False
                )
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.update_stats(elapsed_time, success=True)
                    logger.info(f"🚀 [TTS Fire&Forget] 성공: {elapsed_time:.3f}초")
                else:
                    self.update_stats(elapsed_time, success=False)
                    logger.warning(f"⚠️ [TTS Fire&Forget] 상태 {response.status_code}: {elapsed_time:.3f}초")
                    
            except Exception as e:
                logger.error(f"❌ [TTS Fire&Forget] 백그라운드 오류: {e}")
                self.update_stats(0, success=False)
        
        # 데몬 스레드로 백그라운드 실행
        thread = threading.Thread(target=_send_in_background, daemon=True)
        thread.start()
        
        logger.info(f"🚀 [TTS Fire&Forget] 백그라운드 전송 시작: {tts_message.get('requestId', 'unknown')}")
        
        return {
            'success': True,
            'message': 'TTS 요청이 백그라운드에서 처리 중입니다',
            'method': 'fire_and_forget',
            'background_thread': thread.ident,
            'llm_provider': 'Groq'
        }
    
    def update_stats(self, elapsed_time: float, success: bool = True):
        """성능 통계 업데이트 (스레드 안전)"""
        with self._lock:
            self.stats["total_requests"] += 1
            self.stats["total_time"] += elapsed_time
            
            if success:
                self.stats["success_count"] += 1
            else:
                self.stats["error_count"] += 1
            
            # 성공한 요청만 응답 시간 통계에 포함
            if success and elapsed_time > 0:
                self.stats["avg_time"] = self.stats["total_time"] / self.stats["success_count"] if self.stats["success_count"] > 0 else 0
                self.stats["min_time"] = min(self.stats["min_time"], elapsed_time)
                self.stats["max_time"] = max(self.stats["max_time"], elapsed_time)
    
    def get_current_stats(self) -> Dict[str, Any]:
        """현재 성능 통계 반환"""
        success_rate = (self.stats["success_count"] / self.stats["total_requests"] * 100) if self.stats["total_requests"] > 0 else 0
        
        return {
            "total_requests": self.stats["total_requests"],
            "success_count": self.stats["success_count"],
            "error_count": self.stats["error_count"],
            "success_rate": round(success_rate, 2),
            "avg_response_time": round(self.stats["avg_time"], 3),
            "min_response_time": round(self.stats["min_time"], 3) if self.stats["min_time"] != float('inf') else 0,
            "max_response_time": round(self.stats["max_time"], 3),
            "last_updated": datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """통계 초기화"""
        with self._lock:
            self.stats = {
                "total_requests": 0,
                "total_time": 0,
                "avg_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "success_count": 0,
                "error_count": 0
            }
        logger.info("📊 TTS 클라이언트 통계가 초기화되었습니다")
    
    def health_check(self) -> Dict[str, Any]:
        """TTS 서버 헬스 체크"""
        try:
            start_time = time.time()
            response = self.sync_session.get(
                f"{self.tts_server_url}/health",  # 헬스 체크 엔드포인트
                timeout=(2, 5)
            )
            elapsed_time = time.time() - start_time
            
            return {
                'healthy': response.status_code == 200,
                'status_code': response.status_code,
                'response_time': elapsed_time,
                'server_url': self.tts_server_url
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'server_url': self.tts_server_url
            }
    
    def close(self):
        """리소스 정리"""
        if self.sync_session:
            self.sync_session.close()
            logger.info("🔒 TTS 동기 세션 종료")
    
    async def aclose(self):
        """비동기 리소스 정리"""
        if self.async_session:
            await self.async_session.close()
            logger.info("🔒 TTS 비동기 세션 종료")

# 전역 TTS 클라이언트 인스턴스 (싱글톤)
tts_client = TTSClient()

# 편의 함수들
def send_tts_message(tts_message: Dict[str, Any], method: str = "sync", use_websocket: bool = True) -> Dict[str, Any]:
    """
    TTS 메시지 전송 (편의 함수)
    
    Args:
        tts_message: 전송할 TTS 메시지
        method: 전송 방식 ("sync", "async", "fire_and_forget")
        use_websocket: WebSocket 사용 여부 (기본값: True)
    
    Returns:
        전송 결과
    """
    if method == "sync":
        return tts_client.send_sync_optimized(tts_message, use_websocket=use_websocket)
    elif method == "fire_and_forget":
        return tts_client.send_fire_and_forget(tts_message, use_websocket=use_websocket)
    else:
        raise ValueError(f"동기 함수에서는 '{method}' 방식을 사용할 수 없습니다. 'sync' 또는 'fire_and_forget'을 사용하세요.")

async def send_tts_message_async(tts_message: Dict[str, Any], use_websocket: bool = True) -> Dict[str, Any]:
    """비동기 TTS 메시지 전송 (편의 함수)"""
    return await tts_client.send_async(tts_message, use_websocket=use_websocket)

def get_tts_stats() -> Dict[str, Any]:
    """TTS 클라이언트 통계 조회 (편의 함수)"""
    return tts_client.get_current_stats()