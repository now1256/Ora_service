"""
🚀 Advanced Performance Monitoring System
실시간 성능 모니터링, 자동 최적화, 병목점 탐지
"""
import asyncio
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import psutil
import statistics

logger = logging.getLogger(__name__)

class MetricType(Enum):
    RESPONSE_TIME = "response_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    MODEL_PERFORMANCE = "model_performance"
    SYSTEM_RESOURCE = "system_resource"

@dataclass
class PerformanceMetric:
    timestamp: float
    metric_type: MetricType
    value: float
    metadata: Dict[str, Any]
    source: str

@dataclass  
class SystemSnapshot:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    response_time_avg: float
    cache_hit_rate: float
    error_rate: float
    throughput_per_minute: float
    active_models: int

class PerformanceCollector:
    """성능 메트릭 수집기"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.request_history = deque(maxlen=max_history)
        self.error_history = deque(maxlen=max_history)
        self.cache_stats = deque(maxlen=100)
        self.lock = threading.RLock()
        
        # 실시간 통계
        self.current_minute_requests = 0
        self.current_minute_errors = 0
        self.last_minute_reset = time.time()
    
    def record_request(self, source: str, processing_time: float, 
                      success: bool, cache_hit: bool = False,
                      model_used: str = None, **metadata) -> None:
        """요청 기록"""
        timestamp = time.time()
        
        with self.lock:
            # 요청 히스토리
            self.request_history.append({
                'timestamp': timestamp,
                'source': source,
                'processing_time': processing_time,
                'success': success,
                'cache_hit': cache_hit,
                'model_used': model_used,
                'metadata': metadata
            })
            
            # 분당 요청 수 카운트
            self._update_minute_stats()
            self.current_minute_requests += 1
            
            if not success:
                self.current_minute_errors += 1
                self.error_history.append({
                    'timestamp': timestamp,
                    'source': source,
                    'error': metadata.get('error', 'Unknown error')
                })
            
            # 메트릭 기록
            self.metrics[MetricType.RESPONSE_TIME].append(
                PerformanceMetric(
                    timestamp=timestamp,
                    metric_type=MetricType.RESPONSE_TIME,
                    value=processing_time,
                    metadata={'source': source, 'model': model_used},
                    source=source
                )
            )
    
    def record_cache_stats(self, cache_stats: Dict[str, Any]) -> None:
        """캐시 통계 기록"""
        timestamp = time.time()
        
        with self.lock:
            self.cache_stats.append({
                'timestamp': timestamp,
                **cache_stats
            })
            
            # 캐시 히트율 메트릭
            hit_rate = cache_stats.get('total_hit_rate', 0)
            self.metrics[MetricType.CACHE_HIT_RATE].append(
                PerformanceMetric(
                    timestamp=timestamp,
                    metric_type=MetricType.CACHE_HIT_RATE,
                    value=hit_rate,
                    metadata=cache_stats,
                    source='cache_system'
                )
            )
    
    def _update_minute_stats(self) -> None:
        """분단위 통계 업데이트"""
        current_time = time.time()
        if current_time - self.last_minute_reset >= 60:
            self.current_minute_requests = 0
            self.current_minute_errors = 0
            self.last_minute_reset = current_time
    
    def get_recent_metrics(self, metric_type: MetricType, 
                          duration_seconds: int = 300) -> List[PerformanceMetric]:
        """최근 메트릭 조회"""
        cutoff_time = time.time() - duration_seconds
        
        with self.lock:
            return [
                metric for metric in self.metrics[metric_type]
                if metric.timestamp >= cutoff_time
            ]
    
    def get_system_snapshot(self) -> SystemSnapshot:
        """현재 시스템 스냅샷"""
        with self.lock:
            # 최근 5분 요청들
            recent_requests = [
                req for req in self.request_history
                if time.time() - req['timestamp'] <= 300
            ]
            
            # 응답 시간 평균
            successful_requests = [req for req in recent_requests if req['success']]
            avg_response_time = statistics.mean([
                req['processing_time'] for req in successful_requests
            ]) if successful_requests else 0.0
            
            # 캐시 히트율
            cache_hits = sum(1 for req in recent_requests if req.get('cache_hit'))
            cache_hit_rate = (cache_hits / len(recent_requests) * 100) if recent_requests else 0.0
            
            # 에러율
            error_count = len([req for req in recent_requests if not req['success']])
            error_rate = (error_count / len(recent_requests) * 100) if recent_requests else 0.0
            
            # 분당 처리량
            throughput = len(recent_requests) / 5.0  # 5분 평균
            
            # 시스템 리소스
            memory = psutil.virtual_memory()
            
            return SystemSnapshot(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(),
                memory_percent=memory.percent,
                memory_available_mb=memory.available / 1024 / 1024,
                response_time_avg=avg_response_time,
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                throughput_per_minute=throughput * 12,  # 분당 변환
                active_models=len(set(req.get('model_used') for req in recent_requests if req.get('model_used')))
            )

class AlertManager:
    """알림 관리자"""
    
    def __init__(self):
        self.alert_rules = {
            'high_response_time': {'threshold': 2.0, 'enabled': True},
            'low_cache_hit_rate': {'threshold': 50.0, 'enabled': True},
            'high_error_rate': {'threshold': 10.0, 'enabled': True},
            'high_memory_usage': {'threshold': 80.0, 'enabled': True},
            'high_cpu_usage': {'threshold': 90.0, 'enabled': True}
        }
        self.alert_history = deque(maxlen=100)
        self.last_alerts = {}  # 중복 알림 방지
    
    def check_alerts(self, snapshot: SystemSnapshot) -> List[Dict[str, Any]]:
        """알림 조건 체크"""
        alerts = []
        current_time = time.time()
        
        # 응답 시간 알림
        if (self.alert_rules['high_response_time']['enabled'] and 
            snapshot.response_time_avg > self.alert_rules['high_response_time']['threshold']):
            alert = self._create_alert(
                'high_response_time',
                f"평균 응답 시간이 {snapshot.response_time_avg:.2f}초로 높습니다",
                'warning',
                {'response_time': snapshot.response_time_avg}
            )
            alerts.append(alert)
        
        # 캐시 히트율 알림
        if (self.alert_rules['low_cache_hit_rate']['enabled'] and 
            snapshot.cache_hit_rate < self.alert_rules['low_cache_hit_rate']['threshold']):
            alert = self._create_alert(
                'low_cache_hit_rate',
                f"캐시 히트율이 {snapshot.cache_hit_rate:.1f}%로 낮습니다",
                'warning',
                {'cache_hit_rate': snapshot.cache_hit_rate}
            )
            alerts.append(alert)
        
        # 에러율 알림
        if (self.alert_rules['high_error_rate']['enabled'] and 
            snapshot.error_rate > self.alert_rules['high_error_rate']['threshold']):
            alert = self._create_alert(
                'high_error_rate',
                f"에러율이 {snapshot.error_rate:.1f}%로 높습니다",
                'critical',
                {'error_rate': snapshot.error_rate}
            )
            alerts.append(alert)
        
        # 메모리 사용량 알림
        if (self.alert_rules['high_memory_usage']['enabled'] and 
            snapshot.memory_percent > self.alert_rules['high_memory_usage']['threshold']):
            alert = self._create_alert(
                'high_memory_usage',
                f"메모리 사용량이 {snapshot.memory_percent:.1f}%입니다",
                'warning',
                {'memory_percent': snapshot.memory_percent}
            )
            alerts.append(alert)
        
        # CPU 사용량 알림
        if (self.alert_rules['high_cpu_usage']['enabled'] and 
            snapshot.cpu_percent > self.alert_rules['high_cpu_usage']['threshold']):
            alert = self._create_alert(
                'high_cpu_usage',
                f"CPU 사용량이 {snapshot.cpu_percent:.1f}%입니다",
                'critical',
                {'cpu_percent': snapshot.cpu_percent}
            )
            alerts.append(alert)
        
        # 중복 알림 필터링 및 기록
        filtered_alerts = []
        for alert in alerts:
            alert_key = f"{alert['type']}_{alert['severity']}"
            last_alert_time = self.last_alerts.get(alert_key, 0)
            
            # 5분 이내 동일 알림은 스킵
            if current_time - last_alert_time > 300:
                filtered_alerts.append(alert)
                self.last_alerts[alert_key] = current_time
                self.alert_history.append(alert)
        
        return filtered_alerts
    
    def _create_alert(self, alert_type: str, message: str, severity: str, 
                     metadata: Dict[str, Any]) -> Dict[str, Any]:
        """알림 생성"""
        return {
            'timestamp': time.time(),
            'type': alert_type,
            'message': message,
            'severity': severity,
            'metadata': metadata
        }

class AutoOptimizer:
    """자동 최적화 엔진"""
    
    def __init__(self):
        self.optimization_history = deque(maxlen=50)
        self.last_optimization = 0
        self.optimization_cooldown = 300  # 5분
    
    def suggest_optimizations(self, snapshot: SystemSnapshot, 
                            recent_metrics: Dict[MetricType, List[PerformanceMetric]]) -> List[Dict[str, Any]]:
        """최적화 제안"""
        suggestions = []
        current_time = time.time()
        
        # 쿨다운 체크
        if current_time - self.last_optimization < self.optimization_cooldown:
            return suggestions
        
        # 응답 시간 최적화
        if snapshot.response_time_avg > 1.0:
            if snapshot.cache_hit_rate < 70.0:
                suggestions.append({
                    'type': 'cache_optimization',
                    'priority': 'high',
                    'description': '캐시 히트율이 낮습니다. 캐시 TTL을 늘리거나 더 많은 패턴을 캐싱하세요.',
                    'recommended_actions': [
                        'increase_cache_ttl',
                        'expand_pattern_cache',
                        'enable_predictive_cache'
                    ]
                })
            
            # 병렬 처리 제안
            suggestions.append({
                'type': 'parallel_optimization', 
                'priority': 'medium',
                'description': '응답 시간이 느립니다. 더 많은 LLM을 병렬로 호출하거나 로컬 LLM을 추가하세요.',
                'recommended_actions': [
                    'enable_more_parallel_models',
                    'reduce_model_timeout',
                    'use_faster_models'
                ]
            })
        
        # 리소스 최적화
        if snapshot.memory_percent > 70.0:
            suggestions.append({
                'type': 'memory_optimization',
                'priority': 'medium',
                'description': '메모리 사용량이 높습니다. 캐시 크기를 조정하거나 가비지 컬렉션을 실행하세요.',
                'recommended_actions': [
                    'reduce_cache_size',
                    'cleanup_old_metrics',
                    'optimize_model_loading'
                ]
            })
        
        # 모델 선택 최적화
        response_time_metrics = recent_metrics.get(MetricType.RESPONSE_TIME, [])
        if response_time_metrics:
            model_performance = defaultdict(list)
            for metric in response_time_metrics:
                model = metric.metadata.get('model')
                if model:
                    model_performance[model].append(metric.value)
            
            # 성능이 좋은 모델 추천
            if len(model_performance) > 1:
                avg_times = {
                    model: statistics.mean(times) 
                    for model, times in model_performance.items()
                }
                fastest_model = min(avg_times, key=avg_times.get)
                slowest_model = max(avg_times, key=avg_times.get)
                
                if avg_times[slowest_model] > avg_times[fastest_model] * 2:
                    suggestions.append({
                        'type': 'model_optimization',
                        'priority': 'medium',
                        'description': f'{fastest_model}이 {slowest_model}보다 2배 빠릅니다.',
                        'recommended_actions': [
                            f'prioritize_{fastest_model}',
                            f'reduce_{slowest_model}_usage'
                        ]
                    })
        
        if suggestions:
            self.last_optimization = current_time
            for suggestion in suggestions:
                self.optimization_history.append({
                    'timestamp': current_time,
                    **suggestion
                })
        
        return suggestions

class PerformanceMonitor:
    """통합 성능 모니터링 시스템"""
    
    def __init__(self):
        self.collector = PerformanceCollector()
        self.alert_manager = AlertManager()
        self.optimizer = AutoOptimizer()
        self.monitoring_active = False
        self.monitoring_task = None
        self.dashboard_data = {}
        
        # 모니터링 간격 (초)
        self.monitoring_interval = 30
    
    async def start_monitoring(self) -> None:
        """모니터링 시작"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🚀 성능 모니터링 시작")
    
    async def stop_monitoring(self) -> None:
        """모니터링 중지"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ 성능 모니터링 중지")
    
    async def _monitoring_loop(self) -> None:
        """모니터링 루프"""
        while self.monitoring_active:
            try:
                # 시스템 스냅샷 생성
                snapshot = self.collector.get_system_snapshot()
                
                # 최근 메트릭 수집
                recent_metrics = {}
                for metric_type in MetricType:
                    recent_metrics[metric_type] = self.collector.get_recent_metrics(metric_type, 300)
                
                # 알림 체크
                alerts = self.alert_manager.check_alerts(snapshot)
                for alert in alerts:
                    logger.warning(f"🚨 알림: {alert['message']}")
                
                # 최적화 제안
                suggestions = self.optimizer.suggest_optimizations(snapshot, recent_metrics)
                for suggestion in suggestions:
                    logger.info(f"💡 최적화 제안: {suggestion['description']}")
                
                # 대시보드 데이터 업데이트
                self.dashboard_data = {
                    'snapshot': asdict(snapshot),
                    'alerts': alerts,
                    'suggestions': suggestions,
                    'last_updated': time.time()
                }
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                await asyncio.sleep(5)
    
    def record_request(self, **kwargs) -> None:
        """요청 기록 (외부 인터페이스)"""
        self.collector.record_request(**kwargs)
    
    def record_cache_stats(self, cache_stats: Dict[str, Any]) -> None:
        """캐시 통계 기록 (외부 인터페이스)"""
        self.collector.record_cache_stats(cache_stats)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터 조회"""
        return self.dashboard_data
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """성능 리포트 생성"""
        duration_seconds = hours * 3600
        current_time = time.time()
        
        # 각 메트릭 타입별 통계
        report = {
            'report_period_hours': hours,
            'generated_at': current_time,
            'metrics': {}
        }
        
        for metric_type in MetricType:
            metrics = self.collector.get_recent_metrics(metric_type, duration_seconds)
            if metrics:
                values = [m.value for m in metrics]
                report['metrics'][metric_type.value] = {
                    'count': len(values),
                    'average': statistics.mean(values),
                    'median': statistics.median(values),
                    'min': min(values),
                    'max': max(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0
                }
        
        # 최근 알림
        recent_alerts = [
            alert for alert in self.alert_manager.alert_history
            if current_time - alert['timestamp'] <= duration_seconds
        ]
        report['alerts_summary'] = {
            'total_alerts': len(recent_alerts),
            'by_severity': {
                'critical': len([a for a in recent_alerts if a['severity'] == 'critical']),
                'warning': len([a for a in recent_alerts if a['severity'] == 'warning']),
                'info': len([a for a in recent_alerts if a['severity'] == 'info'])
            }
        }
        
        # 최적화 제안 이력
        recent_optimizations = [
            opt for opt in self.optimizer.optimization_history
            if current_time - opt['timestamp'] <= duration_seconds
        ]
        report['optimization_summary'] = {
            'total_suggestions': len(recent_optimizations),
            'by_type': {}
        }
        
        for opt in recent_optimizations:
            opt_type = opt['type']
            if opt_type not in report['optimization_summary']['by_type']:
                report['optimization_summary']['by_type'][opt_type] = 0
            report['optimization_summary']['by_type'][opt_type] += 1
        
        return report

# 전역 인스턴스
performance_monitor = PerformanceMonitor()