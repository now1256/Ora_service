# 🔐 GitHub Secrets 설정 가이드

## 📋 필수 Secrets 목록

GitHub 리포지토리의 **Settings > Secrets and variables > Actions**에서 다음 secrets를 반드시 추가해야 합니다:

### 1. AWS_OIDC_ROLE_ARN
```
AWS_OIDC_ROLE_ARN: arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_OIDC_ROLE_NAME
```
- **설명**: GitHub Actions가 AWS에 인증할 때 사용할 OIDC 역할 ARN
- **예시**: `arn:aws:iam::319641749746:role/ora-ecr-oicdrole`

## 🔧 AWS OIDC 역할 설정

### 1. IAM 역할 생성

AWS Console에서 IAM → Roles → Create role:

1. **Trusted entity type**: Web identity
2. **Identity provider**: token.actions.githubusercontent.com
3. **Audience**: sts.amazonaws.com
4. **GitHub organization**: `YOUR_GITHUB_USERNAME`
5. **GitHub repository**: `YOUR_REPOSITORY_NAME`

### 2. 신뢰 정책 (Trust Policy)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME:*"
        }
      }
    }
  ]
}
```

### 3. 권한 정책 (Permissions Policy)

다음 권한들을 포함하는 정책을 생성하거나 기존 정책을 연결:

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

또는 AWS 관리 정책 사용:
- `AmazonEC2ContainerRegistryPowerUser`

## 🔧 OIDC Identity Provider 설정

### 1. OIDC Provider 생성 (최초 1회만)

AWS Console에서 IAM → Identity providers → Add provider:

1. **Provider type**: OpenID Connect
2. **Provider URL**: `https://token.actions.githubusercontent.com`
3. **Audience**: `sts.amazonaws.com`

### 2. CLI로 생성하는 방법

```bash
# OIDC Provider 생성
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# 역할 생성
aws iam create-role \
  --role-name ora-ecr-oicdrole \
  --assume-role-policy-document file://trust-policy.json

# 정책 연결
aws iam attach-role-policy \
  --role-name ora-ecr-oicdrole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

## 📦 ECR 리포지토리 설정

### 1. ECR 리포지토리 생성

```bash
# 3개 서비스용 리포지토리 생성
aws ecr create-repository --repository-name llm-server --region ap-northeast-2
aws ecr create-repository --repository-name stt-server --region ap-northeast-2
aws ecr create-repository --repository-name tts-server --region ap-northeast-2
```

### 2. ECR 리포지토리 확인

```bash
# 생성된 리포지토리 확인
aws ecr describe-repositories --region ap-northeast-2
```

## 🔍 설정 검증

### 1. 신뢰 정책 확인

```bash
# 역할의 신뢰 정책 확인
aws iam get-role --role-name ora-ecr-oicdrole --query 'Role.AssumeRolePolicyDocument'
```

### 2. 권한 정책 확인

```bash
# 역할에 연결된 정책 확인
aws iam list-attached-role-policies --role-name ora-ecr-oicdrole
```

### 3. ECR 권한 테스트

```bash
# ECR 로그인 테스트
aws ecr get-login-password --region ap-northeast-2
```

## 🎯 최종 GitHub Secrets 설정

Repository Settings에서 다음 secrets를 추가:

```
AWS_OIDC_ROLE_ARN: arn:aws:iam::YOUR_ACCOUNT_ID:role/ora-ecr-oicdrole
```

## 🚨 보안 고려사항

1. **최소 권한 원칙**: ECR 관련 권한만 부여
2. **리포지토리 제한**: 특정 리포지토리에서만 역할 사용 가능
3. **브랜치 제한**: 필요시 특정 브랜치에서만 사용하도록 제한
4. **모니터링**: CloudTrail로 역할 사용 현황 모니터링

## 🔧 문제 해결

### 1. 인증 오류
```bash
# 역할 ARN 확인
aws iam get-role --role-name ora-ecr-oicdrole --query 'Role.Arn'

# OIDC Provider 확인
aws iam list-open-id-connect-providers
```

### 2. 권한 오류
```bash
# 역할 정책 확인
aws iam list-attached-role-policies --role-name ora-ecr-oicdrole

# 정책 상세 확인
aws iam get-policy --policy-arn POLICY_ARN
```

### 3. ECR 접근 오류
```bash
# ECR 리포지토리 존재 확인
aws ecr describe-repositories --region ap-northeast-2 --repository-names llm-server stt-server tts-server
```

## 💡 팁

- OIDC 방식은 기존 Access Key/Secret Key 방식보다 안전합니다
- 역할 기반 접근으로 임시 자격증명을 사용합니다
- GitHub Actions 실행 시에만 권한이 활성화됩니다
- AWS CloudTrail을 통해 모든 접근을 추적할 수 있습니다 