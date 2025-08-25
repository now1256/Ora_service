#!/usr/bin/env python3
"""
WAV를 Base64로 변환 후 청크 단위로 분할하는 테스트 코드
외부 서버가 받는 데이터 구조를 정확히 확인
"""

import base64
import json

def test_wav_to_base64_chunks(wav_file_path):
    """WAV 파일을 Base64로 변환 후 4096 바이트 청크로 분할"""
    
    print(f"📁 WAV 파일 읽기: {wav_file_path}")
    
    # 1. WAV 파일 읽기
    with open(wav_file_path, 'rb') as f:
        wav_data = f.read()
    
    print(f"✅ WAV 파일 크기: {len(wav_data):,} bytes")
    
    # WAV 헤더 확인
    if wav_data[:4] == b'RIFF' and wav_data[8:12] == b'WAVE':
        print(f"✅ 유효한 WAV 파일")
    
    # 2. 전체 WAV를 Base64로 변환
    print(f"\n🔄 Base64 변환 중...")
    audio_base64 = base64.b64encode(wav_data).decode('utf-8')
    print(f"✅ Base64 크기: {len(audio_base64):,} bytes")
    print(f"   변환 비율: {len(audio_base64) / len(wav_data):.2f}x")
    
    # 3. Base64 문자열을 4096 바이트 청크로 분할
    chunk_size = 4096
    base64_length = len(audio_base64)
    total_chunks = (base64_length + chunk_size - 1) // chunk_size
    
    print(f"\n📦 청크 분할:")
    print(f"   청크 크기: {chunk_size} bytes")
    print(f"   총 청크 수: {total_chunks}개")
    
    # 4. 청크 생성 및 검증
    chunks = []
    for chunk_index in range(total_chunks):
        start_idx = chunk_index * chunk_size
        end_idx = min((chunk_index + 1) * chunk_size, base64_length)
        chunk_base64 = audio_base64[start_idx:end_idx]
        
        chunk_info = {
            'index': chunk_index,
            'size': len(chunk_base64),
            'offset': start_idx,
            'data_preview': chunk_base64[:50] + '...' if len(chunk_base64) > 50 else chunk_base64
        }
        chunks.append(chunk_info)
        
        # 처음 3개와 마지막 청크 정보 출력
        if chunk_index < 3 or chunk_index == total_chunks - 1:
            print(f"   청크 #{chunk_index}: {len(chunk_base64)} bytes (offset: {start_idx})")
    
    # 5. 재조립 검증
    print(f"\n🔍 재조립 검증:")
    reassembled = ''.join([audio_base64[i*chunk_size:(i+1)*chunk_size] for i in range(total_chunks)])
    
    if reassembled == audio_base64:
        print(f"✅ 재조립 성공: Base64가 정확히 일치")
        
        # Base64를 다시 WAV로 디코딩
        reassembled_wav = base64.b64decode(reassembled)
        if reassembled_wav == wav_data:
            print(f"✅ WAV 복원 성공: 원본과 정확히 일치")
        else:
            print(f"❌ WAV 복원 실패")
    else:
        print(f"❌ 재조립 실패")
    
    # 6. 외부 서버가 받는 JSON 구조 예시
    print(f"\n📨 외부 서버가 받는 메시지 예시:")
    example_message = {
        'type': 'audio_chunk',
        'fileName': 'test.wav',
        'chunkIndex': 0,
        'totalChunks': total_chunks,
        'chunkData': chunks[0]['data_preview'],
        'chunkSize': chunks[0]['size'],
        'isLastChunk': False,
        'offset': 0,
        'audioFormat': 'wav_base64'
    }
    print(json.dumps(example_message, indent=2))
    
    print(f"\n💡 외부 서버 재조립 방법:")
    print("1. 모든 청크의 chunkData를 순서대로 합치기")
    print("2. 합친 Base64 문자열을 디코드")
    print("3. 디코딩된 바이너리가 원본 WAV 파일")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        wav_file = sys.argv[1]
    else:
        wav_file = "/path/to/test.wav"
    
    test_wav_to_base64_chunks(wav_file)