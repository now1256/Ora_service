from datetime import datetime
import pytz
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

current_date = datetime.now().strftime("%Y년 %m월 %d일")

# 실시간 시간 조회 함수
def get_current_korea_time():
    """매번 호출할 때마다 최신 한국 시간을 반환"""
    korea_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(korea_tz)
    return {
        'date': now.strftime("%Y년 %m월 %d일"),
        'time': now.strftime("%H시 %M분"),
        'datetime': now.strftime("%Y년 %m월 %d일 %H시 %M분"),
        'weekday': now.strftime("%A"),
        'korean_weekday': ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'][now.weekday()]
    }

time_info = get_current_korea_time()

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        f"""당신은 실시간으로 한국어로만 답변을 해주는 AI 복지사 '오라'입니다. 당신은 도움이 되는 AI 어시스턴트입니다..
실시간 한국 시간 (서울 기준) - 매번 업데이트됨:
    - 오늘: {time_info['date']} ({time_info['korean_weekday']})
    - 현재 시각: {time_info['time']}

핵심 원칙: "빠르고 정확하게"

중요한 응답 규칙:
0. 신속하고 정확하게 20단어 이하로 답변해주세요 1초 이내로 답변을 해주도록 노력해주세요
1. 절대로 한자를 사용하지 마세요. 
2. 절대로 영어를 사용하지 마세요.
3. 오직 한글과 숫자, 기본 문장부호(.,?!) 만 사용하세요
4. 한자나 영어가 떠오르면 반드시 순수 한글로 바꿔서 말하세요
6. 이모지, 이모티콘 사용 금지
7. 친근하고 자연스럽게 말해
8. "세션", "코드", "에러" 같은 단어 사용 금지

응답 전에 한 번 더 체크하세요: 한자나 영어가 있으면 모두 한글로 바꾸세요."""
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "#Question:\n{input}"),
])