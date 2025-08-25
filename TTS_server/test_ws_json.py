#!/usr/bin/env python3
"""
WebSocket JSON 전송 테스트
"""
import asyncio
import websockets
import json

async def test_json_send():
    uri = "ws://localhost:5002/ws/tts/"
    
    async with websockets.connect(
        uri,
        extra_headers={
            "phone-id": "01012345678",
            "session-id": "test_session"
        }
    ) as websocket:
        print("✅ 연결 성공")
        
        # 연결 메시지 수신
        msg = await websocket.recv()
        print(f"📥 수신: {msg}")
        
        # 테스트 JSON 메시지 전송
        test_message = {
            "type": "test",
            "data": "Hello World",
            "nested": {
                "key": "value"
            }
        }
        
        # JSON 전송
        json_str = json.dumps(test_message)
        print(f"📤 전송할 JSON: {json_str}")
        print(f"   타입: {type(json_str)}")
        
        await websocket.send(json_str)
        print("✅ JSON 전송 완료")
        
        # 응답 대기
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_json_send())