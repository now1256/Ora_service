"""
🚀 Multi-Layer Cache System
L0: Memory Cache (0.0001초)
L1: Redis Exact Cache (0.01초)  
L2: Semantic Similarity Cache (0.1초)
L3: Predictive Cache (백그라운드)
"""
import asyncio
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
import threading
from collections import OrderedDict
import numpy as np

logger = logging.getLogger(__name__)

class MemoryCache:
    """L0: 초고속 메모리 캐시"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.access_times = {}
        self.lock = threading.RLock()
    
    def _is_expired(self, key: str) -> bool:
        if key not in self.access_times:
            return True
        return time.time() - self.access_times[key] > self.ttl_seconds
    
    def get(self, key: str) -> Optional[str]:
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                # LRU: 최근 사용으로 이동
                self.cache.move_to_end(key)
                self.access_times[key] = time.time()
                return self.cache[key]
            elif key in self.cache:
                # 만료된 키 제거
                del self.cache[key]
                del self.access_times[key]
        return None
    
    def set(self, key: str, value: str) -> None:
        with self.lock:
            # 최대 크기 초과시 오래된 항목 제거
            while len(self.cache) >= self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                self.access_times.pop(oldest_key, None)
            
            self.cache[key] = value
            self.access_times[key] = time.time()
            self.cache.move_to_end(key)
    
    def clear_expired(self) -> None:
        """만료된 항목들 정리"""
        with self.lock:
            expired_keys = [k for k in self.cache.keys() if self._is_expired(k)]
            for key in expired_keys:
                del self.cache[key]
                del self.access_times[key]
    
    def stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'utilization': len(self.cache) / self.max_size * 100
            }

class SemanticCache:
    """L2: 의미적 유사도 기반 캐시"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        self.similarity_threshold = similarity_threshold
        self.embedding_cache = {}
        self.semantic_index = {}  # {embedding_hash: (query, response, embedding)}
        self.lock = threading.RLock()
    
    def _get_simple_embedding(self, text: str) -> np.ndarray:
        """간단한 TF-IDF 기반 임베딩 (실제론 SentenceTransformer 사용 권장)"""
        # 한국어 불용어
        stop_words = {'은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', '의', '로', '으로'}
        
        # 토큰화 및 불용어 제거
        tokens = [word for word in text.lower().split() if word not in stop_words and len(word) > 1]
        
        # 간단한 해시 기반 벡터 생성 (실제론 더 정교한 방법 필요)
        vector = np.zeros(100)
        for i, token in enumerate(tokens[:10]):  # 최대 10개 토큰
            hash_val = hash(token) % 100
            vector[hash_val] += 1.0 / (i + 1)  # 위치 가중치
        
        # 정규화
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 0 else vector
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """코사인 유사도 계산"""
        try:
            return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        except:
            return 0.0
    
    async def find_similar(self, query: str, phone_id: str) -> Optional[str]:
        """유사한 질문의 답변 찾기"""
        query_embedding = self._get_simple_embedding(query)
        
        with self.lock:
            best_similarity = 0.0
            best_response = None
            
            for key, (cached_query, cached_response, cached_embedding) in self.semantic_index.items():
                if not key.startswith(f"sem:{phone_id}:"):
                    continue
                    
                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_response = cached_response
            
            if best_response:
                logger.info(f"🎯 시맨틱 캐시 히트: 유사도 {best_similarity:.3f}")
                return best_response
        
        return None
    
    async def store(self, query: str, response: str, phone_id: str) -> None:
        """시맨틱 캐시에 저장"""
        query_embedding = self._get_simple_embedding(query)
        key = f"sem:{phone_id}:{hashlib.md5(query.encode()).hexdigest()[:8]}"
        
        with self.lock:
            self.semantic_index[key] = (query, response, query_embedding)
            
            # 최대 크기 제한 (사용자당 50개)
            user_keys = [k for k in self.semantic_index.keys() if k.startswith(f"sem:{phone_id}:")]
            if len(user_keys) > 50:
                # 가장 오래된 것 제거
                oldest_key = min(user_keys)
                del self.semantic_index[oldest_key]

class PredictiveCache:
    """L3: 예측 캐시 - 자주 묻는 질문 미리 생성"""
    
    def __init__(self):
        self.question_patterns = {}
        self.user_patterns = {}
        self.time_patterns = {}
        self.lock = threading.RLock()
    
    def record_question(self, phone_id: str, question: str, response: str) -> None:
        """질문 패턴 기록"""
        with self.lock:
            # 전역 패턴
            question_key = hashlib.md5(question.lower().encode()).hexdigest()[:8]
            if question_key not in self.question_patterns:
                self.question_patterns[question_key] = {'count': 0, 'response': response}
            self.question_patterns[question_key]['count'] += 1
            
            # 사용자별 패턴
            if phone_id not in self.user_patterns:
                self.user_patterns[phone_id] = {}
            if question_key not in self.user_patterns[phone_id]:
                self.user_patterns[phone_id][question_key] = {'count': 0, 'question': question, 'response': response}
            self.user_patterns[phone_id][question_key]['count'] += 1
            
            # 시간대별 패턴
            hour = datetime.now().hour
            if hour not in self.time_patterns:
                self.time_patterns[hour] = {}
            if question_key not in self.time_patterns[hour]:
                self.time_patterns[hour][question_key] = {'count': 0, 'question': question, 'response': response}
            self.time_patterns[hour][question_key]['count'] += 1
    
    def get_popular_questions(self, phone_id: str, limit: int = 10) -> List[Tuple[str, str]]:
        """인기 질문 목록"""
        with self.lock:
            # 사용자별 + 전역 인기 질문
            all_patterns = []
            
            # 사용자 패턴
            if phone_id in self.user_patterns:
                for pattern in self.user_patterns[phone_id].values():
                    all_patterns.append((pattern['question'], pattern['response'], pattern['count'] * 2))  # 사용자 패턴 가중치
            
            # 전역 패턴  
            for pattern in self.question_patterns.values():
                all_patterns.append(("", pattern['response'], pattern['count']))
            
            # 빈도순 정렬
            all_patterns.sort(key=lambda x: x[2], reverse=True)
            
            return [(q, r) for q, r, _ in all_patterns[:limit] if q]

class MultiLayerCache:
    """통합 다층 캐시 시스템"""
    
    def __init__(self):
        self.memory_cache = MemoryCache()
        self.semantic_cache = SemanticCache()
        self.predictive_cache = PredictiveCache()
        
        # 성능 통계
        self.stats = {
            'l0_hits': 0,  # Memory
            'l1_hits': 0,  # Redis Exact
            'l2_hits': 0,  # Semantic
            'l3_hits': 0,  # Predictive
            'misses': 0,
            'total_requests': 0
        }
        
        # 백그라운드 정리 작업 시작
        self._start_cleanup_tasks()
    
    def _generate_cache_key(self, query: str, phone_id: str, cache_type: str = "exact") -> str:
        """캐시 키 생성"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"{cache_type}:{phone_id}:{query_hash}"
    
    async def get(self, query: str, phone_id: str) -> Optional[Dict[str, Any]]:
        """다층 캐시에서 응답 조회"""
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        # L0: Memory Cache (0.0001초)
        memory_key = self._generate_cache_key(query, phone_id, "mem")
        result = self.memory_cache.get(memory_key)
        if result:
            self.stats['l0_hits'] += 1
            logger.info(f"⚡ L0 메모리 캐시 히트: {(time.time() - start_time) * 1000:.2f}ms")
            return {
                'content': result,
                'source': 'L0_memory',
                'processing_time': time.time() - start_time
            }
        
        # L1: Redis Exact Cache (0.01초)
        redis_key = self._generate_cache_key(query, phone_id, "exact")
        result = cache.get(redis_key)
        if result:
            self.stats['l1_hits'] += 1
            # 메모리 캐시에도 저장
            self.memory_cache.set(memory_key, result)
            logger.info(f"💾 L1 Redis 캐시 히트: {(time.time() - start_time) * 1000:.2f}ms")
            return {
                'content': result,
                'source': 'L1_redis',
                'processing_time': time.time() - start_time
            }
        
        # L2: Semantic Similarity Cache (0.1초)
        result = await self.semantic_cache.find_similar(query, phone_id)
        if result:
            self.stats['l2_hits'] += 1
            # 상위 캐시에도 저장
            self.memory_cache.set(memory_key, result)
            cache.set(redis_key, result, timeout=1800)
            logger.info(f"🎯 L2 시맨틱 캐시 히트: {(time.time() - start_time) * 1000:.2f}ms")
            return {
                'content': result,
                'source': 'L2_semantic',
                'processing_time': time.time() - start_time
            }
        
        # L3: Predictive Cache (전역 인기 답변)
        popular_questions = self.predictive_cache.get_popular_questions(phone_id, 5)
        for pop_question, pop_response in popular_questions:
            if self._is_similar_simple(query, pop_question):
                self.stats['l3_hits'] += 1
                # 모든 상위 캐시에 저장
                await self.set(query, pop_response, phone_id)
                logger.info(f"🔮 L3 예측 캐시 히트: {(time.time() - start_time) * 1000:.2f}ms")
                return {
                    'content': pop_response,
                    'source': 'L3_predictive',
                    'processing_time': time.time() - start_time
                }
        
        # 캐시 미스
        self.stats['misses'] += 1
        logger.info(f"❌ 모든 캐시 미스: {(time.time() - start_time) * 1000:.2f}ms")
        return None
    
    async def set(self, query: str, response: str, phone_id: str) -> None:
        """모든 캐시 레이어에 저장"""
        # L0: Memory
        memory_key = self._generate_cache_key(query, phone_id, "mem")
        self.memory_cache.set(memory_key, response)
        
        # L1: Redis
        redis_key = self._generate_cache_key(query, phone_id, "exact")
        cache.set(redis_key, response, timeout=1800)  # 30분
        
        # L2: Semantic
        await self.semantic_cache.store(query, response, phone_id)
        
        # L3: Predictive (패턴 기록)
        self.predictive_cache.record_question(phone_id, query, response)
        
        logger.info(f"💾 모든 레이어에 캐싱 완료: {query[:30]}...")
    
    def _is_similar_simple(self, query1: str, query2: str) -> bool:
        """간단한 유사도 체크"""
        if not query2:
            return False
        
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union > 0.6 if union > 0 else False
    
    def _start_cleanup_tasks(self) -> None:
        """백그라운드 정리 작업 시작"""
        def cleanup_worker():
            while True:
                try:
                    # 5분마다 정리 작업
                    time.sleep(300)
                    self.memory_cache.clear_expired()
                    logger.info("🧹 캐시 정리 작업 완료")
                except Exception as e:
                    logger.error(f"캐시 정리 오류: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 성능 통계"""
        total = self.stats['total_requests']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'l0_hit_rate': self.stats['l0_hits'] / total * 100,
            'l1_hit_rate': self.stats['l1_hits'] / total * 100,
            'l2_hit_rate': self.stats['l2_hits'] / total * 100,
            'l3_hit_rate': self.stats['l3_hits'] / total * 100,
            'total_hit_rate': (total - self.stats['misses']) / total * 100,
            'memory_stats': self.memory_cache.stats()
        }

# 전역 인스턴스
multi_cache = MultiLayerCache()