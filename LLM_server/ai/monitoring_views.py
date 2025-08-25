"""
🚀 Ultra Fast LLM 시스템 모니터링 및 관리 API
성능 모니터링, 시스템 상태, 최적화 제어를 위한 엔드포인트
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .ultra_fast_llm import ultra_fast_llm
from .monitoring.performance_monitor import performance_monitor
from .cache.multi_layer_cache import multi_cache
from .llm.parallel_llm import parallel_llm
from .llm.local_llm import local_llm_system

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['GET'])
async def health_check(request):
    """전체 시스템 헬스 체크"""
    try:
        health_status = await ultra_fast_llm.health_check()
        
        status_code = status.HTTP_200_OK
        if health_status['overall_status'] == 'unhealthy':
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_status['overall_status'] == 'degraded':
            status_code = status.HTTP_206_PARTIAL_CONTENT
        
        return Response(health_status, status=status_code)
        
    except Exception as e:
        logger.error(f"헬스 체크 오류: {e}")
        return Response({
            'overall_status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['GET'])
def system_stats(request):
    """시스템 통계 조회"""
    try:
        stats = ultra_fast_llm.get_system_stats()
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"시스템 통계 조회 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['GET'])
def performance_dashboard(request):
    """성능 대시보드 데이터"""
    try:
        dashboard_data = performance_monitor.get_dashboard_data()
        return Response(dashboard_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['GET'])
def performance_report(request):
    """성능 리포트 생성"""
    try:
        hours = int(request.GET.get('hours', 24))
        report = performance_monitor.get_performance_report(hours)
        return Response(report, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"성능 리포트 생성 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
async def optimize_system(request):
    """시스템 자동 최적화 실행"""
    try:
        optimization_result = await ultra_fast_llm.optimize_system()
        return Response(optimization_result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"시스템 최적화 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['GET'])
def cache_stats(request):
    """캐시 시스템 통계"""
    try:
        cache_stats = multi_cache.get_cache_stats()
        return Response(cache_stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"캐시 통계 조회 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['DELETE'])
def clear_cache(request):
    """캐시 정리"""
    try:
        # 메모리 캐시 정리
        multi_cache.memory_cache.clear_expired()
        
        # 성능 카운터 리셋
        multi_cache.stats = {
            'l0_hits': 0, 'l1_hits': 0, 'l2_hits': 0, 'l3_hits': 0,
            'misses': 0, 'total_requests': 0
        }
        
        return Response({
            'success': True,
            'message': '캐시가 정리되었습니다'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"캐시 정리 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['GET'])
async def llm_health(request):
    """LLM 시스템별 상태 체크"""
    try:
        results = {
            'parallel_llm': await parallel_llm.health_check(),
            'local_llm': await local_llm_system.health_check(),
            'timestamp': performance_monitor.collector.get_system_snapshot().timestamp
        }
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"LLM 헬스 체크 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
async def test_response_speed(request):
    """응답 속도 테스트"""
    try:
        data = json.loads(request.body)
        test_query = data.get('query', '안녕하세요')
        phone_id = data.get('phoneId', 'test-speed')
        iterations = int(data.get('iterations', 10))
        
        results = []
        
        for i in range(iterations):
            start_time = performance_monitor.collector.request_history[-1]['timestamp'] if performance_monitor.collector.request_history else 0
            
            response = await ultra_fast_llm.generate_response(test_query, phone_id)
            
            results.append({
                'iteration': i + 1,
                'processing_time': response.get('processing_time', 0),
                'strategy_used': response.get('strategy_used', 'unknown'),
                'cache_hit': response.get('cache_hit', False),
                'success': response.get('content') is not None
            })
        
        # 통계 계산
        successful_results = [r for r in results if r['success']]
        avg_time = sum(r['processing_time'] for r in successful_results) / len(successful_results) if successful_results else 0
        cache_hit_rate = sum(1 for r in results if r['cache_hit']) / len(results) * 100
        
        return Response({
            'test_query': test_query,
            'iterations': iterations,
            'results': results,
            'summary': {
                'average_response_time': avg_time,
                'success_rate': len(successful_results) / len(results) * 100,
                'cache_hit_rate': cache_hit_rate,
                'fastest_time': min(r['processing_time'] for r in successful_results) if successful_results else 0,
                'slowest_time': max(r['processing_time'] for r in successful_results) if successful_results else 0
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"속도 테스트 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
async def initialize_system(request):
    """시스템 강제 초기화"""
    try:
        logger.info("🚀 Ultra Fast LLM 시스템 강제 초기화 시작...")
        
        success = await ultra_fast_llm.initialize()
        
        if success:
            return Response({
                'success': True,
                'message': 'Ultra Fast LLM 시스템이 성공적으로 초기화되었습니다',
                'system_stats': ultra_fast_llm.get_system_stats()
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': '시스템 초기화에 실패했습니다'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"시스템 초기화 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt  
@api_view(['GET'])
def monitoring_summary(request):
    """모니터링 요약 정보"""
    try:
        # 시스템 스냅샷
        snapshot = performance_monitor.collector.get_system_snapshot()
        
        # 캐시 통계
        cache_stats = multi_cache.get_cache_stats()
        
        # LLM 통계
        parallel_stats = parallel_llm.get_stats()
        local_stats = local_llm_system.get_system_stats()
        
        summary = {
            'system_health': {
                'response_time_avg': snapshot.response_time_avg,
                'cache_hit_rate': snapshot.cache_hit_rate,
                'error_rate': snapshot.error_rate,
                'throughput_per_minute': snapshot.throughput_per_minute,
                'cpu_percent': snapshot.cpu_percent,
                'memory_percent': snapshot.memory_percent
            },
            'cache_performance': {
                'total_hit_rate': cache_stats.get('total_hit_rate', 0),
                'l0_hit_rate': cache_stats.get('l0_hit_rate', 0),
                'l1_hit_rate': cache_stats.get('l1_hit_rate', 0),
                'l2_hit_rate': cache_stats.get('l2_hit_rate', 0),
                'memory_utilization': cache_stats.get('memory_stats', {}).get('utilization', 0)
            },
            'llm_performance': {
                'parallel_success_rate': parallel_stats.get('success_rate', 0),
                'local_llm_initialized': local_stats.get('is_initialized', False),
                'active_providers': parallel_stats.get('enabled_providers', 0),
                'model_wins': parallel_stats.get('model_wins', {})
            },
            'recommendations': []
        }
        
        # 성능 기반 추천사항
        if snapshot.response_time_avg > 1.0:
            summary['recommendations'].append({
                'type': 'performance',
                'message': '평균 응답 시간이 높습니다. 캐시 최적화를 고려하세요.',
                'priority': 'high'
            })
        
        if snapshot.cache_hit_rate < 60.0:
            summary['recommendations'].append({
                'type': 'cache',
                'message': '캐시 히트율이 낮습니다. 캐시 정책을 검토하세요.',
                'priority': 'medium'
            })
        
        if snapshot.error_rate > 5.0:
            summary['recommendations'].append({
                'type': 'reliability',
                'message': '에러율이 높습니다. 시스템 로그를 확인하세요.',
                'priority': 'high'
            })
        
        return Response(summary, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"모니터링 요약 오류: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)