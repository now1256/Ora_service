"""
LLM_server HTTP 클라이언트
공통 HTTP 클라이언트를 LLM_server에서 사용할 수 있도록 import
"""
import sys
import os

# 공통 HTTP 클라이언트 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

try:
    from shared.infrastructure.http_client import http_client
    
    # LLM_server 전용 HTTP 클라이언트 (공통 클라이언트 활용)
    llm_http_client = http_client
    
except ImportError:
    # 공통 클라이언트를 찾을 수 없는 경우 None으로 설정
    llm_http_client = None
    print("⚠️ 공통 HTTP 클라이언트를 찾을 수 없습니다. requests를 직접 사용합니다.") 