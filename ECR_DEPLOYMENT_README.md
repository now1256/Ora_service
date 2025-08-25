# 🚀 ECR 배포 가이드

## 📋 개요
3개의 AI 서버를 AWS ECR에 동시에 배포하는 GitHub Actions 워크플로우입니다.

## 🤖 서버 구성
- **🧠 LLM Server**: 대화형 AI 모델 서버
- **🎤 STT Server**: 음성을 텍스트로 변환
- **🔊 TTS Server**: 텍스트를 음성으로 변환

## 🔧 설정 방법

### 1. AWS 설정
📋 **`AWS_설정_가이드.md` 파일을 참고하여 AWS 설정을 완료하세요.**

### 2. GitHub Secrets 설정
**🎉 GitHub Secrets 설정이 필요하지 않습니다!**

워크플로우에 모든 값이 하드코딩되어 있습니다:
- AWS 계정 ID: `319641749746`
- AWS 리전: `ap-northeast-2`

## 🚀 실행 방법

### 자동 실행
- 모든 브랜치에 push할 때 자동 실행

### 수동 실행
1. GitHub **Actions** 탭으로 이동
2. "🚀 ECR 배포" 워크플로우 선택
3. **Run workflow** 버튼 클릭

## 🏷️ 이미지 태그 규칙

- `latest`: 최신 빌드 이미지
- `{커밋SHA}`: 특정 커밋의 고유 이미지

### 예시
```
319641749746.dkr.ecr.ap-northeast-2.amazonaws.com/llm-server:latest
319641749746.dkr.ecr.ap-northeast-2.amazonaws.com/llm-server:a1b2c3d4
```

## 🔄 배포 프로세스

1. **🔐 AWS 인증**: OIDC 방식으로 안전하게 인증
2. **🏪 ECR 로그인**: Amazon ECR에 로그인
3. **🐳 병렬 빌드**: 3개 서버 동시 빌드
4. **⬆️ ECR 푸시**: 각 서버 이미지 푸시

## 🐳 로컬에서 이미지 사용하기

```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 319641749746.dkr.ecr.ap-northeast-2.amazonaws.com

# 이미지 Pull & 실행
docker pull 319641749746.dkr.ecr.ap-northeast-2.amazonaws.com/llm-server:latest
docker run -d -p 5000:5000 319641749746.dkr.ecr.ap-northeast-2.amazonaws.com/llm-server:latest
```

## 🔍 로그 확인

GitHub Actions에서 다음과 같은 로그를 확인할 수 있습니다:

```
🎯 배포 대상: llm-server
📝 설명: 대화형 AI 모델 서버
🔨 Docker 이미지 빌드 시작...
✅ 빌드 완료! (소요시간: 1234초)
⬆️ ECR에 이미지 푸시 시작...
✅ 푸시 완료! (소요시간: 567초)
🎉 배포 성공!
```

## 🚨 주의사항

1. **빌드 시간**: CUDA 이미지는 빌드 시간이 길 수 있습니다 (15-30분)
2. **OIDC 인증**: 더 안전한 인증 방식 사용
3. **모든 브랜치**: 모든 브랜치에서 실행되므로 주의하세요

## 📚 추가 도움말

- **AWS 설정**: `AWS_설정_가이드.md` 참고
- **상세 설정**: `GITHUB_SECRETS_SETUP.md` 참고 