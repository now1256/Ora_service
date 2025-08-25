# AWS OIDC 역할 및 ECR 리포지토리 생성 스크립트
# 실행 전 AWS CLI 인증 필요: aws configure

Write-Host "🚀 AWS OIDC 역할 및 ECR 리포지토리 생성 시작..." -ForegroundColor Green

$AWS_ACCOUNT_ID = "319641749746"
$AWS_REGION = "ap-northeast-2"
$ROLE_NAME = "ora-ecr-oicdrole"

# 신뢰 정책 파일 생성
$TrustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
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
"@

$TrustPolicy | Out-File -FilePath "trust-policy.json" -Encoding utf8

Write-Host "📝 신뢰 정책 파일 생성 완료" -ForegroundColor Yellow

# IAM 역할 생성 또는 업데이트
Write-Host "🔐 IAM 역할 생성/업데이트 중..." -ForegroundColor Blue

try {
    # 역할이 이미 있는지 확인
    aws iam get-role --role-name $ROLE_NAME 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "⚠️  역할이 이미 존재합니다. 신뢰 정책을 업데이트합니다." -ForegroundColor Yellow
        aws iam update-assume-role-policy --role-name $ROLE_NAME --policy-document file://trust-policy.json
    } else {
        Write-Host "✨ 새로운 역할을 생성합니다." -ForegroundColor Green
        aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json
    }
} catch {
    Write-Host "❌ 역할 생성/업데이트 실패: $($_.Exception.Message)" -ForegroundColor Red
}

# ECR 권한 정책 연결
Write-Host "🔗 ECR 권한 정책 연결 중..." -ForegroundColor Blue
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"

# ECR 리포지토리 생성
$repositories = @("llm-server", "stt-server", "tts-server")

Write-Host "📦 ECR 리포지토리 생성 중..." -ForegroundColor Blue

foreach ($repo in $repositories) {
    Write-Host "  📁 $repo 리포지토리 생성 중..." -ForegroundColor Cyan
    try {
        aws ecr create-repository --repository-name $repo --region $AWS_REGION 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ $repo 리포지토리 생성 완료" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  $repo 리포지토리가 이미 존재합니다." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❌ $repo 리포지토리 생성 실패" -ForegroundColor Red
    }
}

# 임시 파일 정리
Remove-Item -Path "trust-policy.json" -Force

Write-Host "`n🎉 설정 완료!" -ForegroundColor Green
Write-Host "💡 GitHub Actions를 다시 실행해보세요." -ForegroundColor Yellow

# 역할 정보 확인
Write-Host "`n📋 생성된 역할 정보:" -ForegroundColor Cyan
aws iam get-role --role-name $ROLE_NAME --query "Role.{RoleName:RoleName,Arn:Arn,CreateDate:CreateDate}" 