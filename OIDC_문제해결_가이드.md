# 🚨 OIDC 인증 에러 해결 가이드

## 🔍 에러 상황
```
Error: Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

## 📋 해결 단계

### 1️⃣ GitHub Secrets 확인
먼저 GitHub 리포지토리 Settings → Secrets and variables → Actions에서 다음 secrets가 설정되어 있는지 확인하세요:

- **AWS_ACCOUNT_ID**: `319641749746`
- **AWS_REGION**: `ap-northeast-2`

### 2️⃣ GitHub 리포지토리 정보 확인
워크플로우를 실행하여 다음 정보를 확인하세요:

```
🔍 AWS 설정 확인
📂 GitHub 리포지토리: PASCAL-ORA/OraAiServer
🔗 GitHub Actor: YOUR_USERNAME
🌿 GitHub Ref: refs/heads/main
```

### 3️⃣ AWS IAM에서 OIDC Identity Provider 확인

#### AWS 콘솔에서 확인
1. **AWS IAM 콘솔** → **Identity providers**
2. `https://token.actions.githubusercontent.com` 프로바이더가 있는지 확인

#### CLI로 확인
```bash
aws iam list-open-id-connect-providers
```

**없으면 생성:**
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 4️⃣ IAM 역할 `ora-ecr-oicdrole` 확인

#### 역할 존재 여부 확인
```bash
aws iam get-role --role-name ora-ecr-oicdrole
```

#### 역할이 없으면 생성
```bash
# 신뢰 정책 파일 생성 (trust-policy.json)
cat > trust-policy.json << EOF
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
          "token.actions.githubusercontent.com:sub": "repo:PASCAL-ORA/OraAiServer:*"
        }
      }
    }
  ]
}
EOF

# 역할 생성
aws iam create-role \
  --role-name ora-ecr-oicdrole \
  --assume-role-policy-document file://trust-policy.json
```

### 5️⃣ 신뢰 정책 수정 (가장 중요!)

#### 현재 신뢰 정책 확인
```bash
aws iam get-role --role-name ora-ecr-oicdrole --query 'Role.AssumeRolePolicyDocument'
```

#### 신뢰 정책 업데이트
```bash
# 올바른 신뢰 정책 생성 (AWS_ACCOUNT_ID = 319641749746)
cat > trust-policy-fixed.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::\${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:PASCAL-ORA/OraAiServer:*"
        }
      }
    }
  ]
}
EOF

# 신뢰 정책 업데이트
aws iam update-assume-role-policy \
  --role-name ora-ecr-oicdrole \
  --policy-document file://trust-policy-fixed.json
```

### 6️⃣ ECR 권한 정책 연결

```bash
# ECR 권한 정책 연결
aws iam attach-role-policy \
  --role-name ora-ecr-oicdrole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

### 7️⃣ ECR 리포지토리 생성

```bash
# 3개 ECR 리포지토리 생성
aws ecr create-repository --repository-name llm-server --region ap-northeast-2
aws ecr create-repository --repository-name stt-server --region ap-northeast-2
aws ecr create-repository --repository-name tts-server --region ap-northeast-2
```

## 🔍 문제 진단 체크리스트

### ✅ 확인 사항
- [ ] OIDC Identity Provider가 존재하는가?
- [ ] IAM 역할 `ora-ecr-oicdrole`이 존재하는가?
- [ ] 신뢰 정책에서 GitHub 리포지토리가 `PASCAL-ORA/OraAiServer`로 정확한가?
- [ ] ECR 권한 정책이 연결되어 있는가?
- [ ] ECR 리포지토리 3개가 생성되어 있는가?

### 🚨 일반적인 실수들

1. **리포지토리 이름 오타**
   ```
   잘못: PASCAL-ORA/oraaiserver
   올바름: PASCAL-ORA/OraAiServer
   ```

2. **계정 ID 오타**
   ```
   잘못: arn:aws:iam::123456789:oidc-provider/...
   올바름: arn:aws:iam::$AWS_ACCOUNT_ID:oidc-provider/...
   ```

3. **브랜치 제한**
   ```
   문제: "repo:PASCAL-ORA/OraAiServer:ref:refs/heads/main"
   해결: "repo:PASCAL-ORA/OraAiServer:*"
   ```

## 💡 빠른 해결 방법

### 전체 설정을 한 번에 실행
```bash
#!/bin/bash
# GitHub Secrets 값 설정
export AWS_ACCOUNT_ID="319641749746"
export AWS_REGION="ap-northeast-2"

# OIDC Provider 생성
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# 신뢰 정책 파일 생성
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:PASCAL-ORA/OraAiServer:*"
        }
      }
    }
  ]
}
EOF

# IAM 역할 생성 또는 업데이트
aws iam create-role \
  --role-name ora-ecr-oicdrole \
  --assume-role-policy-document file://trust-policy.json \
  || aws iam update-assume-role-policy \
    --role-name ora-ecr-oicdrole \
    --policy-document file://trust-policy.json

# ECR 권한 연결
aws iam attach-role-policy \
  --role-name ora-ecr-oicdrole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# ECR 리포지토리 생성
aws ecr create-repository --repository-name llm-server --region ${AWS_REGION}
aws ecr create-repository --repository-name stt-server --region ${AWS_REGION}
aws ecr create-repository --repository-name tts-server --region ${AWS_REGION}

echo "✅ OIDC 설정 완료!"
```

## 🎯 테스트 방법

설정 완료 후 GitHub Actions를 다시 실행하여 다음 로그를 확인:

```
🔐 AWS 인증 설정 (OIDC)
✅ AWS 인증 확인
🔍 AWS 인증 상태 확인...
{
    "UserId": "AROAXXXXXXXXXXXXXXXXX:GitHubActions-llm-server-XXXXXX",
    "Account": "319641749746",
    "Arn": "arn:aws:sts::319641749746:assumed-role/ora-ecr-oicdrole/GitHubActions-llm-server-XXXXXX"
}
✅ AWS 인증 성공!
```

### 🎯 GitHub Secrets 설정
반드시 GitHub 리포지토리의 **Settings → Secrets and variables → Actions**에서 다음을 설정하세요:

1. **AWS_ACCOUNT_ID**: `319641749746`
2. **AWS_REGION**: `ap-northeast-2`

이 가이드대로 진행하면 OIDC 인증 문제가 해결됩니다! 🚀 