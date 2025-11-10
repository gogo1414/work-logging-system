# Terraform 배포 가이드

Terraform과 GitHub Actions를 활용해 **일간 REST API(FastAPI 컨테이너)**와 향후 주간/월간 배치 스크립트를 AWS 서버리스 환경으로 배포하는 절차를 정리했습니다. 모든 명령은 프로젝트 루트에서 실행하며, Docker 이미지를 빌드한 뒤 Terraform에 이미지 URI를 전달하는 흐름을 기본으로 합니다.

## 1. 사전 준비

1. Terraform CLI 1.5 이상 설치
2. AWS 자격 증명 준비 (`aws configure` 또는 GitHub Secrets에 저장)
3. Notion API 키와 `API_AUTH_TOKEN`을 **SSM Parameter Store SecureString**으로 저장
4. Docker가 설치된 환경에서 `docker build` 실행 가능 여부 확인

## 2. Docker 이미지 빌드 및 ECR 업로드

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 1) 도커 이미지 빌드
docker build -t work-logging-api:local .

# 2) ECR 로그인 & 리포지토리 생성(최초 1회)
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com
aws ecr create-repository --repository-name work-logging-system/api

# 3) 태그 및 푸시
docker tag work-logging-api:local <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/work-logging-system/api:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/work-logging-system/api:latest
```

생성된 `docker_image_uri` 값은 Terraform 변수에 입력하거나 GitHub Actions 워크플로우 입력으로 전달합니다.

## 3. 환경별 변수 정의

`infra/terraform/environments/dev/terraform.tfvars.example` 파일을 참고해 환경별 변수를 정의합니다. 필수 항목은 **컨테이너 이미지 URI**, **Notion DB ID 3개**, **SSM Parameter 이름 2개**뿐입니다.

```hcl
# infra/terraform/environments/dev/terraform.tfvars
docker_image_uri             = "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/work-logging-system/api:latest"
notion_db1_id                = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
notion_db2_id                = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
notion_db3_id                = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ssm_parameter_notion_api_key = "/work-logging/notion_api_key"
ssm_parameter_api_auth_token = "/work-logging/api_auth_token"
```

## 4. Terraform 초기화 및 배포

환경별 디렉터리로 이동한 뒤 원격 상태 파일을 구성하고 배포합니다.

```bash
cd infra/terraform/environments/dev
terraform init \
  -backend-config="../../backends/dev.hcl"

terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

운영 환경(prod)도 동일한 구조로 확장 가능하며, `backends/prod.hcl`과 전용 tfvars 파일을 별도로 준비합니다.

## 5. GitHub Actions 배포 파이프라인

`.github/workflows/deploy.yml` 워크플로우는 다음 두 단계로 구성됩니다.

1. **Docker 이미지 빌드 & ECR 푸시**
   - `workflow_dispatch` 입력값으로 `image_tag` 지정 가능
   - GitHub Secrets에 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` 저장 필요
2. **Terraform Plan/Apply**
   - `inputs.apply` 값을 `true`로 설정하면 `terraform apply` 실행
   - `TF_VAR_docker_image_uri` 환경 변수로 Lambda가 사용할 이미지 URI 주입

> plan만 실행하려면 `apply=false`로 수동 트리거하면 됩니다.

## 6. 배포 후 점검 항목

- `terraform output api_endpoint`로 반환된 URL에 `GET /health` 호출 → 200 OK 확인
- Parameter Store의 SecureString 값이 올바르게 주입되었는지 Lambda 환경 변수 확인
- CloudWatch Logs(`/aws/lambda/<함수명>`)에서 FastAPI 실행 로그 및 오류 여부 확인

## 7. 롤백 및 개선

- `terraform destroy -var-file=terraform.tfvars`로 전체 리소스 회수
- API 오류 시 GitHub Actions를 통해 새 이미지를 빌드/재배포
- 향후 EventBridge 스케줄러(주간/월간) 모듈을 추가해 동일 스택에서 관리 예정
