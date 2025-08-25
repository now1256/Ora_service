# 🔧 AWS 설정 가이드

## 📋 필수 설정 순서

### 1️⃣ OIDC Identity Provider 생성 (최초 1회만)

#### AWS 콘솔에서 설정
1. **AWS IAM 콘솔** → **Identity providers** → **Add provider**
2. **Provider type**: `OpenID Connect`
3. **Provider URL**: `https://token.actions.githubusercontent.com`
4. **Audience**: `sts.amazonaws.com`
5. **Add provider** 클릭

#### AWS CLI로 설정
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2️⃣ IAM 역할 생성

#### AWS 콘솔에서 설정
1. **AWS IAM 콘솔** → **Roles** → **Create role**
2. **Trusted entity type**: `Web identity`
3. **Identity provider**: `token.actions.githubusercontent.com`
4. **Audience**: `sts.amazonaws.com`
5. **GitHub organization**: `YOUR_GITHUB_USERNAME`
6. **GitHub repository**: `YOUR_REPOSITORY_NAME`
7. **Role name**: `ora-ecr-oicdrole` (또는 원하는 이름)

#### 신뢰 정책 (Trust Policy)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::319641749746:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/OraAiServer:*"
        }
      }
    }
  ]
}
```

### 3️⃣ ECR 권한 정책 연결

#### 옵션 1: AWS 관리 정책 사용 (권장)
```bash
aws iam attach-role-policy \
  --role-name ora-ecr-oicdrole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

#### 옵션 2: 커스텀 정책 생성
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "*"
    }
  ]
}
```

### 4️⃣ ECR 리포지토리 생성

#### AWS 콘솔에서 설정
1. **Amazon ECR 콘솔** → **Repositories** → **Create repository**
2. **Repository name**: `llm-server`
3. **Create repository** 클릭
4. **stt-server**, **tts-server**도 동일하게 생성

#### AWS CLI로 설정
```bash
# 3개 리포지토리 생성
aws ecr create-repository --repository-name llm-server --region ap-northeast-2
aws ecr create-repository --repository-name stt-server --region ap-northeast-2
aws ecr create-repository --repository-name tts-server --region ap-northeast-2
```

### 5️⃣ GitHub Secrets 설정

**🎉 GitHub Secrets 설정이 필요하지 않습니다!**

워크플로우에서 다음 값들이 하드코딩되어 있습니다:
- **AWS 계정 ID**: `319641749746`
- **AWS 리전**: `ap-northeast-2`
- **IAM 역할**: `ora-ecr-oicdrole`

따라서 별도의 GitHub Secrets 설정 없이 바로 사용할 수 있습니다.

## 🔍 설정 확인 방법

### 1. 역할 확인
```bash
# 생성된 역할 확인
aws iam get-role --role-name ora-ecr-oicdrole

# 역할에 연결된 정책 확인
aws iam list-attached-role-policies --role-name ora-ecr-oicdrole
```

### 2. ECR 리포지토리 확인
```bash
# 생성된 리포지토리 확인
aws ecr describe-repositories --region ap-northeast-2
```

### 3. OIDC Provider 확인
```bash
# OIDC Provider 확인
aws iam list-open-id-connect-providers
```

## 📝 실제 설정값

### 워크플로우에 하드코딩된 값들
```
AWS 계정 ID: 319641749746
AWS 리전: ap-northeast-2
IAM 역할: ora-ecr-oicdrole
```

### 신뢰 정책 예시
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::319641749746:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/OraAiServer:*"
        }
      }
    }
  ]
}
```

## 🚨 주의사항

1. **계정 ID 고정**: AWS 계정 ID `319641749746`에 맞게 설정됨
2. **GitHub 정보 변경**: `YOUR_GITHUB_USERNAME`을 실제 GitHub 사용자명으로 변경
3. **리전 설정**: 모든 리소스는 `ap-northeast-2` (서울) 리전에 생성
4. **권한 최소화**: ECR 관련 권한만 부여하여 보안 강화

## 🎯 완료 후 테스트

GitHub Actions를 실행하여 정상 동작 확인:
1. 코드 push 또는 수동 실행
2. 로그에서 AWS 인증 성공 확인
3. ECR에 이미지 푸시 성공 확인

## 💡 유용한 명령어

```bash
# AWS 계정 ID 확인
aws sts get-caller-identity --query Account --output text

# ECR 로그인 테스트
aws ecr get-login-password --region ap-northeast-2

# 푸시된 이미지 확인
aws ecr list-images --repository-name llm-server --region ap-northeast-2
``` 