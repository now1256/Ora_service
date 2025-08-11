# Ora Service – 노인복지를 위한 AI 음성 플랫폼

> **"AI가 말벗이 되고, 기억을 이어주는 노인복지 음성 서비스"**  
> 2025년부터 진행된 **오라(Ora) 서비스 플랫폼**은 음성 기반 대화형 AI 기술을 활용하여  
> 노년층의 정서적·정보적 복지를 지원합니다.

## 서비스 개요

<img width="1095" alt="Ora Service Flow" src="https://github.com/user-attachments/assets/b3607a29-f48a-463b-a3ab-63e61516a39b" />

오라는 노년층이 **손쉽게 음성으로 대화**하며  
- 일상적인 말벗 기능  
- 복지 정보 안내  
- 개인 맞춤형 답변 제공  
을 받을 수 있는 **AI 음성 상호작용 플랫폼**입니다.

---

## 기술 스택

| 분야 | 기술 |
|------|------|
| **AI 프레임워크** | [LangChain](https://www.langchain.com/) (LLM 기반 대화 관리) |
| **음성 인식 (STT)** | [OpenAI Whisper](https://openai.com/research/whisper) |
| **음성 합성 (TTS)** | [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) |
| **백엔드/배포** | Docker, Django |
| **데이터베이스** | [Weaviate](https://weaviate.io/) (벡터 검색 기반 컨텍스트 저장) |
| **모델 환경** | CUDA, PyTorch |


## 서비스 구조
```
음성 입력 → STT 서버 → 텍스트 변환 → LLM 서버 → AI 응답 → TTS 서버 → 음성 출력
    ↓           ↓           ↓           ↓           ↓           ↓
Weaviate ← 대화 기록 저장 ← 벡터 검색 ← 컨텍스트 분석 ← 개인화 응답
```

## 성과

### 수상 내역
<table>
<tr>
<td align="center" width="50%">
  
<img src="https://github.com/user-attachments/assets/44be398f-90bb-4e2c-b9a3-d116fb998214" width="500" /><br>
<b>강원대학교 창업혁신원장상</b>

</td>
<td align="center" width="50%">

<img src="https://github.com/user-attachments/assets/beb0c42b-ade3-439e-88ab-095d39e40df7" width="500" /><br>
<b>보건복지부 장관상</b>

</td>
</tr>
</table>

### 팀 & 기여
- AI 모델 개발: STT/TTS 최적화, 한국어 대화 자연도 개선
- TTS 기존 성능기준 생성소도 5초 -> 0초내로 최적화, Streaming 기능 구현
