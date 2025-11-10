# Terraform 기반 배포 구조

이 디렉터리는 업무 자동 로깅 시스템을 AWS 서버리스 환경으로 배포하기 위한 Terraform 구성을 관리합니다. 핵심 목표는 **일간 REST API(컨테이너 기반 Lambda + API Gateway)**와 주간/월간 배치 작업을 하나의 인프라 스택에서 관리하면서, 필요한 비밀정보와 실행 패키지를 안전하게 주입하는 것입니다.

## 디렉터리 구성 제안

```
infra/terraform/
├── backends/
│   └── dev.hcl                   # 원격 상태 저장소 설정 예시
├── environments/
│   └── dev/
│       ├── main.tf               # 개발 환경 스택 정의
│       ├── variables.tf          # 입력 변수
│       ├── outputs.tf            # 주요 출력
│       └── terraform.tfvars.example
└── modules/
    └── aws_api_lambda/
        ├── main.tf               # Lambda + API Gateway 구성
        ├── variables.tf
        └── outputs.tf
```

현재 저장소에는 템플릿만 두고, 실제 리소스 정의는 각 환경에서 점진적으로 추가할 예정입니다.

## 주요 모듈 설명

### `modules/aws_api_lambda`

- **필수 입력값은 `docker_image_uri` + Notion DB ID/Parameter 이름뿐**이며, 나머지는 모듈 내부에서 기본값으로 처리됩니다.
- API Gateway HTTP API + Lambda 조합으로 `/daily-logs`, `/health` 엔드포인트를 노출
- Lambda는 **ECR에 업로드한 컨테이너 이미지**를 사용 (FastAPI 서버)
- 환경 변수는 평문 값(`environment_variables`)과 SSM SecureString 파라미터(`ssm_parameters`)를 병합하여 주입
- CloudWatch Logs 보존 기간은 14일로 고정되어 있으며, 추가 태그나 메모리/타임아웃 조정 옵션은 제거했습니다.
- 출력값으로 Lambda ARN과 API 엔드포인트 제공

> 주간/월간 배치(weekly/monthly processor)는 추후 동일 모듈 또는 별도 EventBridge 스케줄러 모듈로 확장 예정입니다.

## 상태 관리 및 보안

- Terraform 상태는 **S3 + DynamoDB** 조합을 권장하며, `backends/dev.hcl` 파일을 참고해 환경별로 분리
- `.env` 파일은 커밋하지 않고, 민감 정보는 Parameter Store(또는 Secrets Manager)에 저장 후 모듈 입력값으로 전달
- `API_AUTH_TOKEN`, `NOTION_API_KEY` 등은 SecureString으로 저장 후 Lambda 환경 변수로 복호화 주입

## 운영 흐름 요약

1. 로컬 혹은 GitHub Actions에서 Docker 이미지를 빌드해 ECR로 푸시
2. `infra/terraform/environments/<env>/` 디렉터리에서 `terraform plan/apply` 실행
3. 배포 완료 후 출력되는 `api_endpoint` 값과 SSM에 보관한 토큰으로 API 호출
4. CloudWatch Logs를 통해 Lambda 실행 상태 모니터링

> `deploy/terraform.md`에는 컨테이너 이미지 빌드/푸시, Terraform 실행 절차, GitHub Actions 파이프라인 예시가 정리되어 있습니다.
