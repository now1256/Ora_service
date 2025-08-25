#!/usr/bin/env python3
"""
TTS WebSocket 스트리밍 테스트 스크립트
"""

import json
import time
import requests
import sys
import os

# Django 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TTS_server.settings')

def test_http_mode():
    """HTTP 전송 모드 테스트"""
    print("\n" + "="*60)
    print("📡 HTTP 전송 모드 테스트")
    print("="*60)
    
    url = "http://localhost:5002/api/convert-tts/"
    
    data = {
        "text": "안녕하세요. HTTP 전송 모드 테스트입니다.",
        "phoneId": "test-phone-http",
        "sessionId": "test-session-http",
        "requestId": f"test-request-http-{int(time.time())}",
        "use_websocket": False,  # HTTP 모드
        "fire_and_forget": False
    }
    
    print(f"요청 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=data)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 성공! (소요 시간: {elapsed_time:.3f}초)")
            print(f"응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"\n❌ 실패! 상태 코드: {response.status_code}")
            print(f"응답: {response.text}")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

def test_websocket_mode():
    """WebSocket 전송 모드 테스트"""
    print("\n" + "="*60)
    print("🔌 WebSocket 전송 모드 테스트")
    print("="*60)
    
    url = "http://localhost:5002/api/convert-tts/"
    
    data = {
        "text": "안녕하세요. WebSocket 스트리밍 모드 테스트입니다. 이것은 청크 단위로 전송됩니다.",
        "phoneId": "test-phone-ws",
        "sessionId": "test-session-ws",
        "requestId": f"test-request-ws-{int(time.time())}",
        "use_websocket": True,  # WebSocket 모드
        "fire_and_forget": True  # Fire-and-forget
    }
    
    print(f"요청 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=data)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 성공! (소요 시간: {elapsed_time:.3f}초)")
            print(f"응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"\n❌ 실패! 상태 코드: {response.status_code}")
            print(f"응답: {response.text}")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

def test_websocket_sync_mode():
    """WebSocket 동기 모드 테스트 (완료까지 대기)"""
    print("\n" + "="*60)
    print("🔌 WebSocket 동기 모드 테스트 (완료까지 대기)")
    print("="*60)
    
    url = "http://localhost:5002/api/convert-tts/"
    
    data = {
        "text": "WebSocket 동기 모드 테스트입니다. 전송이 완료될 때까지 대기합니다.",
        "phoneId": "test-phone-ws-sync",
        "sessionId": "test-session-ws-sync",
        "requestId": f"test-request-ws-sync-{int(time.time())}",
        "use_websocket": True,  # WebSocket 모드
        "fire_and_forget": False  # 동기 모드
    }
    
    print(f"요청 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=data)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 성공! (소요 시간: {elapsed_time:.3f}초)")
            print(f"응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"\n❌ 실패! 상태 코드: {response.status_code}")
            print(f"응답: {response.text}")
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

def test_performance_comparison():
    """성능 비교 테스트"""
    print("\n" + "="*60)
    print("📊 성능 비교 테스트")
    print("="*60)
    
    url = "http://localhost:5002/api/convert-tts/"
    test_text = "이것은 성능 비교를 위한 테스트 문장입니다. WebSocket과 HTTP 전송 방식의 속도를 비교합니다."
    
    # HTTP 테스트
    http_times = []
    for i in range(3):
        data = {
            "text": test_text,
            "phoneId": f"perf-test-http-{i}",
            "sessionId": f"perf-session-http-{i}",
            "requestId": f"perf-request-http-{int(time.time())}-{i}",
            "use_websocket": False,
            "fire_and_forget": False
        }
        
        start_time = time.time()
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                elapsed_time = time.time() - start_time
                http_times.append(elapsed_time)
                print(f"HTTP 테스트 {i+1}: {elapsed_time:.3f}초")
        except Exception as e:
            print(f"HTTP 테스트 {i+1} 실패: {e}")
    
    # WebSocket 테스트
    ws_times = []
    for i in range(3):
        data = {
            "text": test_text,
            "phoneId": f"perf-test-ws-{i}",
            "sessionId": f"perf-session-ws-{i}",
            "requestId": f"perf-request-ws-{int(time.time())}-{i}",
            "use_websocket": True,
            "fire_and_forget": True
        }
        
        start_time = time.time()
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                elapsed_time = time.time() - start_time
                ws_times.append(elapsed_time)
                print(f"WebSocket 테스트 {i+1}: {elapsed_time:.3f}초")
        except Exception as e:
            print(f"WebSocket 테스트 {i+1} 실패: {e}")
    
    # 결과 분석
    if http_times and ws_times:
        http_avg = sum(http_times) / len(http_times)
        ws_avg = sum(ws_times) / len(ws_times)
        
        print("\n" + "="*40)
        print("📈 성능 비교 결과")
        print("="*40)
        print(f"HTTP 평균 응답 시간: {http_avg:.3f}초")
        print(f"WebSocket 평균 응답 시간: {ws_avg:.3f}초")
        print(f"개선율: {((http_avg - ws_avg) / http_avg * 100):.1f}%")

def main():
    """메인 테스트 함수"""
    print("🎯 TTS WebSocket 스트리밍 테스트 시작")
    print("="*60)
    
    # 서버 헬스 체크
    try:
        response = requests.get("http://localhost:5002/health")
        if response.status_code != 200:
            print("❌ TTS 서버가 응답하지 않습니다.")
            return
        print("✅ TTS 서버 정상 작동 중")
    except Exception as e:
        print(f"❌ TTS 서버 연결 실패: {e}")
        return
    
    # 각 모드 테스트
    test_http_mode()
    time.sleep(1)
    
    test_websocket_mode()
    time.sleep(1)
    
    test_websocket_sync_mode()
    time.sleep(1)
    
    test_performance_comparison()
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    main()