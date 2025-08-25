from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from .tools import tools
from .prompts import prompt
import os

api_key = os.getenv("OPENAI_API_KEY")

# ⚡ 초고속 LLM 설정 - Agent용 최적화
llm = ChatOpenAI(
    model="gpt-4o-mini",  # 가장 빠른 모델
    temperature=0,        # 창의성 제거로 속도 최대화
    api_key=api_key,
    base_url="https://api.openai.com/v1",
    timeout=2,            # 더 짧은 타임아웃 (3초 → 2초)
    max_retries=0,        # 재시도 완전 제거
    max_tokens=80,        # 응답 길이 증가 (50 → 80자)
    request_timeout=1.5,  # 매우 짧은 요청 타임아웃 (2초 → 1.5초)
)

agent = create_tool_calling_agent(llm, tools, prompt)

# ⚡ 초고속 AgentExecutor 설정 - 속도 최우선
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=False,                    # 로깅 제거로 속도 향상
    max_iterations=2,                 # 더 줄임 (3 → 2)
    max_execution_time=3,             # 더 짧은 실행 시간 (5초 → 3초)
    early_stopping_method="generate", # 자연스러운 응답 생성
    return_intermediate_steps=False,  # 중간 단계 반환 안함
    handle_parsing_errors=True,       # 파싱 오류 처리
    # 추가 최적화 옵션
    trim_intermediate_steps=10,       # 중간 단계 트림
)
