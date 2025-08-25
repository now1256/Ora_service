#!/usr/bin/env python3
"""
WebSocket 수신 테스트 - 실제 데이터가 전송되는지 확인
"""
import asyncio
import websockets
import json

async def test_receive():
    uri = "ws://localhost:5002/ws/tts/"
    
    async with websockets.connect(
        uri,
        extra_headers={
            "phone-id": "01012345678",
            "session-id": "test_session"
        }
    ) as websocket:
        print("✅ WebSocket 연결 성공!")
        
        # 연결 메시지 수신
        message = await websocket.recv()
        print(f"📥 수신: {json.loads(message)['type']}")
        
        # 데이터 수신 대기
        print("⏳ 데이터 수신 대기 중...")
        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=60)
                data = json.loads(message)
                
                if 'audioDataBase64' in data:
                    print(f"📦 청크 수신: {data['chunkIndex']}, 크기: {len(data['audioDataBase64'])} bytes")
                elif data.get('status') == 'complete':
                    print(f"✅ 전송 완료: 총 {data['totalChunks']}개 청크")
                    break
                else:
                    print(f"📥 메시지: {data.get('type', 'unknown')}")
                    
            except asyncio.TimeoutError:
                print("⏱️ 60초 동안 데이터 없음")
                break

if __name__ == "__main__":
    asyncio.run(test_receive())