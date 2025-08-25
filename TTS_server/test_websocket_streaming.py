#!/usr/bin/env python3
"""
WebSocket WAV 스트리밍 테스트 스크립트
WAV 파일을 4096 바이트 청크로 나누어 전송하는 예제
"""

import asyncio
import websockets
import json
import base64
import time
import sys

async def stream_wav_file(wav_file_path, websocket_url, phone_id="test123", session_id="session456"):
    """WAV 파일을 읽어서 WebSocket으로 스트리밍"""
    
    print(f"📁 WAV 파일 읽기: {wav_file_path}")
    
    # WAV 파일 읽기
    with open(wav_file_path, 'rb') as f:
        wav_data = f.read()
    
    print(f"📊 WAV 파일 크기: {len(wav_data):,} bytes")
    
    # WAV 헤더 확인
    if wav_data[:4] == b'RIFF' and wav_data[8:12] == b'WAVE':
        print("✅ 유효한 WAV 파일 형식")
    else:
        print("⚠️ WAV 파일 형식이 아닐 수 있음")
    
    # WebSocket 연결
    headers = {
        "phone-id": phone_id,
        "session-id": session_id
    }
    
    print(f"🔌 WebSocket 연결 중: {websocket_url}")
    
    async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
        print("✅ WebSocket 연결 성공")
        
        # 연결 확인 메시지 수신
        response = await websocket.recv()
        print(f"📨 서버 응답: {json.loads(response)['type']}")
        
        # 청크 크기 설정
        chunk_size = 4096  # 4KB
        total_chunks = (len(wav_data) + chunk_size - 1) // chunk_size
        
        print(f"📦 청크 수: {total_chunks}개 (청크 크기: {chunk_size} bytes)")
        print("🚀 스트리밍 시작...")
        
        start_time = time.time()
        bytes_sent = 0
        
        # WAV 바이너리를 청크로 나누어 전송
        for chunk_index in range(total_chunks):
            # 청크 추출
            start_idx = chunk_index * chunk_size
            end_idx = min((chunk_index + 1) * chunk_size, len(wav_data))
            chunk_bytes = wav_data[start_idx:end_idx]
            
            # Base64 인코딩 (JSON 전송을 위해)
            chunk_base64 = base64.b64encode(chunk_bytes).decode('utf-8')
            
            # 청크 메시지 생성
            chunk_message = {
                'type': 'audio_chunk_test',
                'chunkIndex': chunk_index,
                'totalChunks': total_chunks,
                'chunkData': chunk_base64,
                'chunkSize': len(chunk_bytes),
                'isLastChunk': chunk_index == total_chunks - 1,
                'offset': start_idx
            }
            
            # 청크 전송
            await websocket.send(json.dumps(chunk_message))
            
            bytes_sent += len(chunk_bytes)
            
            # 진행률 표시
            if chunk_index % 10 == 0 or chunk_index == total_chunks - 1:
                progress = (bytes_sent / len(wav_data)) * 100
                elapsed = time.time() - start_time
                speed = bytes_sent / elapsed / 1024 if elapsed > 0 else 0
                
                print(f"   📡 진행: {progress:.1f}% ({bytes_sent:,}/{len(wav_data):,} bytes)")
                print(f"      청크 {chunk_index + 1}/{total_chunks}, 속도: {speed:.1f} KB/s")
            
            # 실시간 스트리밍 시뮬레이션 (옵션)
            # await asyncio.sleep(0.01)  # 10ms 딜레이
        
        # 전송 완료
        total_time = time.time() - start_time
        throughput = len(wav_data) / total_time / 1024
        
        print(f"\n✅ 스트리밍 완료!")
        print(f"   ⏱️ 전송 시간: {total_time:.3f}초")
        print(f"   📈 평균 속도: {throughput:.1f} KB/s")
        print(f"   📊 청크당 평균: {total_time / total_chunks * 1000:.1f}ms")

if __name__ == "__main__":
    # 테스트 설정
    WAV_FILE = "/path/to/test.wav"  # 테스트할 WAV 파일 경로
    WEBSOCKET_URL = "ws://localhost:5002/ws/tts/"
    
    if len(sys.argv) > 1:
        WAV_FILE = sys.argv[1]
    
    print("🎵 WAV 스트리밍 테스트 시작")
    print("=" * 50)
    
    # 비동기 실행
    asyncio.run(stream_wav_file(WAV_FILE, WEBSOCKET_URL))