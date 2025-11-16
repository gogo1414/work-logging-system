# 업무 자동 로깅 및 이력서 관리 시스템

회사 프로젝트에서 수행한 업무를 실시간으로 정리하고, 주간·월간 단위로 자동 요약해 이력서에 활용할 수 있도록 돕는 저장소입니다. 실제 개발 업무는 회사 환경에서 진행되며, 이 저장소는 **업무 기록 자동화 스크립트·REST API·인프라 정의를 관리**하는 목적으로 사용합니다.

## 목차

- [프로젝트 개요](#프로젝트-개요)
- [주요 기능](#주요-기능)
- [아키텍처](#아키텍처)
- [빠른 시작 (5분 배포)](#빠른-시작-5분-배포)
  - [1단계: Notion 설정](#1단계-notion-설정)
  - [2단계: Render 배포](#2단계-render-배포)
  - [3단계: API 테스트](#3단계-api-테스트)
- [LLM 제공자 선택](#llm-제공자-선택)
- [REST API 명세](#rest-api-명세)
- [운영 및 모니터링](#운영-및-모니터링)
- [로컬 개발 환경](#로컬-개발-환경)
  - [가상환경 설정](#가상환경-설정)
  - [환경 변수 구성](#환경-변수-구성)
  - [Docker 실행](#docker-실행)
  - [테스트](#테스트)
- [고급 배포 옵션](#고급-배포-옵션)
  - [AWS Lambda 배포](#aws-lambda-배포)
  - [자체 서버 배포](#자체-서버-배포)

## 프로젝트 개요

일일 업무를 Notion에 자동으로 기록하고, LLM으로 주간·월간 성과를 요약하여 이력서 작성을 자동화하는 시스템입니다.

**현재 배포 상태:**

- ✅ Render 무료 플랜으로 24/7 운영 중
- ✅ REST API: https://work-logging-system.onrender.com
- ✅ 마크다운 → Notion 블록 자동 변환
- ✅ 다중 LLM 지원 (Claude/ChatGPT/Gemini)

## 주요 기능

### 📝 일간 로그 자동화

- REST API로 Cursor/Claude에서 직접 업무 기록
- STAR 구조 (Situation-Task-Action-Result) 자동 포맷팅
- 마크다운이 Notion 블록 (헤딩, 리스트)으로 변환

### 🤖 LLM 기반 요약

- **주간 요약**: 7일치 로그를 핵심 성과로 압축
- **월간 요약**: 주간 성과를 이력서용 문장으로 정리
- Claude, ChatGPT, Gemini 중 선택 가능

### ☁️ 간편한 배포

- **Render**: GitHub 연결만으로 5분 내 배포 완료
- **자동 재배포**: Git push 시 자동 배포
- **무료 운영**: 무료 플랜으로 충분한 사용량

## 아키텍처

### 1. API 플로우 (일간 로그)

```mermaid
sequenceDiagram
    participant User as Cursor/Claude
    participant API as FastAPI (Lambda)
    participant Notion as Notion DB1
    participant Log as logs/execution.log

    User->>API: POST /daily-logs (Bearer Token)
    API->>API: 요청 검증 (STAR 구조)
    API->>Notion: create_daily_log()
    Notion-->>API: page_id, url
    API->>Log: 실행 로그 기록
    API-->>User: 201 Created + Notion URL
```

### 2. 주간/월간 자동화 플로우

```mermaid
flowchart LR
    A[EventBridge Scheduler] -->|주간 트리거| B[weekly_processor.py]
    A -->|월간 트리거| C[monthly_processor.py]
    B --> D[Notion DB1<br/>Daily Logs]
    D --> E[LLM API<br/>STAR 요약]
    E --> F[Notion DB2<br/>Weekly Achievements]
    C --> F
    F --> G[LLM API<br/>월간 하이라이트]
    G --> H[Notion DB3<br/>Monthly Highlights]
```

### 3. AWS 인프라 구성

```mermaid
graph TB
    subgraph "GitHub Actions CI/CD"
        GH[GitHub Repo]
        GH -->|1. Docker Build| ECR[AWS ECR]
        GH -->|2. Terraform Apply| TF[Terraform State<br/>S3 + DynamoDB]
    end

    subgraph "AWS Serverless"
        APIGW[API Gateway<br/>HTTP API] --> Lambda[Lambda Container<br/>FastAPI]
        Lambda --> SSM[SSM Parameter Store<br/>API Keys]
        Lambda --> CW[CloudWatch Logs]
        EventBridge[EventBridge Scheduler] -.->|향후| Lambda2[Weekly/Monthly Lambda]
    end

    Lambda --> Notion[Notion API]
    Lambda --> LLM[LLM API<br/>Claude/ChatGPT/Gemini]
    ECR -.->|이미지| Lambda
```

## 빠른 시작 (5분 배포)

GitHub 연결만으로 5분 내에 운영 환경을 구축할 수 있습니다.

### 1단계: Notion 설정

#### 1-1. Notion Integration 생성

1. https://www.notion.so/my-integrations 접속
2. `+ New integration` 클릭
   - Name: `Work Logging System`
   - Type: `Internal Integration`
3. 발급된 토큰 복사 (나중에 Render 환경 변수로 사용)

#### 1-2. Notion 데이터베이스 생성

**Daily Work Logs 데이터베이스:**

1. Notion에서 새 페이지 생성 → 제목: `Daily Work Logs`
2. `/table` 입력 → `Table - Inline` 선택
3. 필수 속성 추가:
   - `Name` (Title) - 기본 제공
   - `Logged Date` (Date)
   - `Category` (Select) - 신규기능, 버그픽스, 성능개선 등
   - `Impact Level` (Select) - High, Medium, Low
   - `Tech Stack` (Multi-select)
   - `Status` (Select) - Logged, In Review, Published
   - `Metrics` (Text)
   - `Ticket URL` (URL)
4. 페이지 우측 상단 `⋯` → `Connections` → `Work Logging System` 연결
5. 페이지 URL에서 데이터베이스 ID 추출 (하이픈 제거한 32자리)

**Weekly/Monthly 데이터베이스 (선택사항):**

주간/월간 요약 기능을 사용하려면 동일한 방식으로 2개 더 생성:

- `Weekly Achievements` (Period Start/End, Bullet Points 등)
- `Monthly Highlights` (Year-Month, Summary 등)

### 2단계: Render 배포

#### 2-1. GitHub 저장소 연결

1. https://render.com 접속 → GitHub로 로그인
2. `New +` → `Blueprint` 선택
3. 이 저장소 연결 (fork하거나 자신의 저장소로 복사)

#### 2-2. 환경 변수 설정

Render 대시보드 → 생성된 서비스 선택 → `Environment` 탭:

```bash
# 필수 환경 변수
NOTION_API_KEY=secret_xxxx...        # 1단계에서 복사한 토큰
NOTION_DB1_ID=xxxxxxxx...            # Daily Work Logs DB ID (32자리, 하이픈 제거)
API_AUTH_TOKEN=your_secure_token     # API 호출 시 사용할 비밀번호

# LLM 설정 (하나만 선택)
LLM_PROVIDER=claude                  # claude | openai | gemini
CLAUDE_API_KEY=sk-ant-xxx...         # Claude 사용 시
# 또는
OPENAI_API_KEY=sk-xxx...             # ChatGPT 사용 시
# 또는
GEMINI_API_KEY=xxx...                # Gemini 사용 시

# 선택사항 (주간/월간 요약 사용 시)
NOTION_DB2_ID=xxx...                 # Weekly Achievements DB ID
NOTION_DB3_ID=xxx...                 # Monthly Highlights DB ID
```

#### 2-3. 배포 완료 대기

- Render가 자동으로 Docker 이미지 빌드 및 배포 (약 2-3분 소요)
- 배포 완료 후 할당된 URL 확인 (예: `https://your-app.onrender.com`)

### 3단계: API 테스트

**Health check:**

```bash
curl https://your-app.onrender.com/health
```

**Daily log 생성:**

```bash
curl -X POST https://your-app.onrender.com/daily-logs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_secure_token" \
  -d '{
    "title": "첫 번째 업무 로그 테스트",
    "context": "### Situation\n테스트 로그입니다.\n\n### Task\nRender 배포를 확인합니다.\n\n### Action\n- API 호출\n- Notion 저장 확인\n\n### Result\n정상 작동 확인",
    "category": "기타",
    "impact_level": "Low",
    "tech_stack": ["Render", "FastAPI"],
    "logged_date": "2025-11-16"
  }'
```

성공하면 Notion 페이지 URL이 반환됩니다!

---

**🎉 배포 완료!** 이제 Cursor나 다른 도구에서 이 API를 호출하여 자동으로 업무를 기록할 수 있습니다.

## LLM 제공자 선택

주간/월간 요약 기능에서 사용할 LLM을 선택할 수 있습니다.

### 지원하는 LLM

| 제공자             | 모델                 | 특징                                 |
| ------------------ | -------------------- | ------------------------------------ |
| **Claude** (기본)  | claude-sonnet-4      | 한국어 품질 최고, 컨텍스트 이해 우수 |
| **OpenAI ChatGPT** | gpt-4o               | 범용성 높음, 안정적 성능             |
| **Google Gemini**  | gemini-2.0-flash-exp | 무료 티어 관대, 응답 빠름            |

### 설정 방법

Render 환경 변수에서 `LLM_PROVIDER`와 해당 API 키만 설정:

```bash
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-xxx...
```

또는

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx...
```

**API 키 발급:**

- Claude: https://console.anthropic.com
- OpenAI: https://platform.openai.com
- Gemini: https://aistudio.google.com

## REST API 명세

### 인증

- 환경 변수 `API_AUTH_TOKEN`이 설정되어 있으면 `Authorization: Bearer <토큰>` 헤더 필수
- 토큰이 비어 있으면 인증 없이 호출 가능(개발용)

### 엔드포인트

| Method | Path          | 설명                                    |
| ------ | ------------- | --------------------------------------- |
| GET    | `/health`     | 헬스 체크                               |
| POST   | `/daily-logs` | 일일 업무 로그 생성 후 Notion DB에 저장 |

### 외부 협업자용 가이드

외부 팀원이나 다른 프로젝트에서 이 API를 활용할 때는 아래 템플릿과 작성 가이드를 참고하세요.

#### 필드별 작성 가이드

| 필드           | 타입                | 필수 여부 | 설명                                                                                |
| -------------- | ------------------- | --------- | ----------------------------------------------------------------------------------- |
| `title`        | string              | 필수      | 업무 내용을 한 줄로 요약 (예: "결제 API 성능 개선", "사용자 알림 기능 추가")        |
| `context`      | string              | 필수      | STAR 구조(Situation, Task, Action, Result)로 작성, 각 섹션은 `### 헤딩`으로 시작    |
| `category`     | string              | 필수      | 업무 유형: `신규기능`, `성능개선`, `버그픽스`, `리팩토링`, `문서화`, `기타` 중 선택 |
| `impact_level` | string              | 필수      | 영향도: `High`, `Medium`, `Low` 중 선택                                             |
| `tech_stack`   | array[string]       | 필수      | 사용한 기술 스택 목록 (예: `["Python", "FastAPI", "Docker"]`)                       |
| `logged_date`  | string (YYYY-MM-DD) | 선택      | 작업 날짜, 미입력 시 서버 현재 날짜 사용                                            |
| `status`       | string              | 선택      | 상태: `Logged`, `In Review`, `Published` 등 (기본값: `Logged`)                      |
| `metrics`      | string              | 선택      | 정량 지표 (예: "응답속도 300ms → 80ms 개선", "테스트 커버리지 85% 달성")            |
| `ticket_url`   | string              | 선택      | 관련 이슈 트래커 URL (Jira, GitHub Issue 등)                                        |

#### STAR 구조 작성 예시

`context` 필드는 다음 형식으로 작성합니다. 각 섹션은 **`### Situation`**, **`### Task`**, **`### Action`**, **`### Result`** 헤딩으로 명확히 구분하세요.

**템플릿:**

```
### Situation
(배경과 문제 상황을 설명)

### Task
(해결해야 할 과제나 목표)

### Action
(실제 수행한 작업, 불릿 포인트로 세부 내용 나열 가능)

### Result
(결과와 성과, 가능하면 정량 지표 포함)
```

**실제 작성 예:**

```
### Situation
사내 로그는 CLI 수동 입력만 제공돼 Notion 자동 기록·이력 관리가 지연되고 있었습니다.

### Task
Cursor/Claude와 연동되는 REST API를 Docker+AWS Lambda 환경에 배포해 실시간 자동화를 확립해야 했습니다.

### Action
- FastAPI `/daily-logs` 엔드포인트와 Bearer 인증 구현, Notion DB 속성 매핑 및 상세 오류 로깅
- Docker 이미지, GitHub Actions, Terraform(AWS Lambda+API Gateway)으로 최소 비용 인프라 구성
- weekly/monthly 파이프라인을 포함한 통합 테스트 10건 작성, README/운영 문서에 명세 기록

### Result
로컬 Docker 실행만으로 Notion 자동 기록이 가능해졌고, 테스트 10건 자동 실행으로 회귀 위험을 제거했으며, Lambda 기반으로 고정비 없이 운영할 수 있게 되었습니다.
```

#### 복사용 JSON 템플릿

```json
{
  "title": "<업무 내용을 한 줄로 요약>",
  "context": "### Situation\n<배경과 문제 상황>\n\n### Task\n<해결해야 할 과제>\n\n### Action\n<실제 수행한 작업>\n\n### Result\n<결과와 성과>",
  "category": "<신규기능|성능개선|버그픽스|리팩토링|문서화|기타>",
  "impact_level": "<High|Medium|Low>",
  "tech_stack": ["<기술1>", "<기술2>"],
  "logged_date": "YYYY-MM-DD",
  "status": "Logged",
  "metrics": "<정량 지표 (선택)>",
  "ticket_url": "<이슈 URL (선택)>"
}
```

#### 실제 요청 예시 (curl)

```bash
curl -X POST https://your-api-endpoint.com/daily-logs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "title": "REST API 기반 일간 로그 자동화 구축",
    "context": "### Situation\n사내 로그는 CLI 수동 입력만 제공돼 Notion 자동 기록·이력 관리가 지연되고 있었습니다.\n\n### Task\nCursor/Claude와 연동되는 REST API를 Docker+AWS Lambda 환경에 배포해 실시간 자동화를 확립해야 했습니다.\n\n### Action\n- FastAPI `/daily-logs` 엔드포인트와 Bearer 인증 구현, Notion DB 속성 매핑 및 상세 오류 로깅\n- Docker 이미지, GitHub Actions, Terraform(AWS Lambda+API Gateway)으로 최소 비용 인프라 구성\n- weekly/monthly 파이프라인을 포함한 통합 테스트 10건 작성, README/운영 문서에 명세 기록\n\n### Result\n로컬 Docker 실행만으로 Notion 자동 기록이 가능해졌고, 테스트 10건 자동 실행으로 회귀 위험을 제거했으며, Lambda 기반으로 고정비 없이 운영할 수 있게 되었습니다.",
    "category": "신규기능",
    "impact_level": "High",
    "tech_stack": ["Python", "FastAPI", "Docker", "AWS Lambda", "API Gateway", "Terraform", "GitHub Actions", "Anthropic Claude"],
    "logged_date": "2025-11-09",
    "status": "Logged",
    "metrics": "REST API 자동화 도입, 통합 테스트 10건 자동 실행, Notion 일간 로그 실시간 기록",
    "ticket_url": null
  }'
```

#### 성공 응답

```json
{
  "page_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "url": "https://notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

#### 오류 코드

| 코드 | 설명                                         |
| ---- | -------------------------------------------- |
| 400  | 요청 본문 검증 실패 (예: 날짜 형식 오류)     |
| 401  | 인증 실패 (`Authorization` 헤더 누락/불일치) |
| 500  | Notion API 호출 실패 등 서버 오류            |

#### 주의 사항

- JSON 내부의 `\n`은 줄바꿈을 의미하므로, 실제 요청 시 이스케이프 처리가 필요합니다.
- `context` 필드는 반드시 문자열로 전송해야 하며, 배열이나 객체 형태는 허용되지 않습니다.
- `category`와 `impact_level`은 Notion DB에 정의된 Select 옵션과 일치해야 합니다.
- Swagger 문서는 서버 실행 후 `/docs` 엔드포인트에서 확인 가능합니다.

> **협업 팁:** 외부 팀원에게 이 가이드를 공유하면, Notion DB 구조나 내부 필드명을 모르더라도 템플릿을 채워서 요청을 보낼 수 있습니다. Cursor/Claude 등 LLM 도구에 이 템플릿을 제공하면 자동으로 STAR 구조에 맞춰 정리해 줄 수 있습니다.

## LLM 제공자 선택

이 프로젝트는 여러 LLM 제공자를 지원합니다. 환경 변수 `LLM_PROVIDER`로 사용할 LLM을 선택할 수 있습니다.

### 지원하는 LLM 제공자

| 제공자              | 모델                     | 환경 변수        | API 키 발급                   |
| ------------------- | ------------------------ | ---------------- | ----------------------------- |
| **Claude** (기본값) | claude-sonnet-4-20250514 | `CLAUDE_API_KEY` | https://console.anthropic.com |
| **OpenAI ChatGPT**  | gpt-4o                   | `OPENAI_API_KEY` | https://platform.openai.com   |
| **Google Gemini**   | gemini-2.0-flash-exp     | `GEMINI_API_KEY` | https://aistudio.google.com   |

### 설정 방법

1. `.env` 파일에 원하는 LLM 제공자와 API 키를 설정합니다:

```bash
# LLM 제공자 선택 (claude | openai | gemini)
LLM_PROVIDER=claude

# 선택한 제공자의 API 키 설정
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 또는
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 또는
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

2. 스크립트 실행 시 자동으로 선택한 LLM이 사용됩니다:

```bash
# 주간 요약 생성 (설정된 LLM 사용)
python scripts/weekly_processor.py --dry-run

# 월간 요약 생성 (설정된 LLM 사용)
python scripts/monthly_processor.py --dry-run
```

### LLM 제공자 비교

| 항목               | Claude     | OpenAI ChatGPT | Google Gemini |
| ------------------ | ---------- | -------------- | ------------- |
| **한국어 품질**    | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐       | ⭐⭐⭐⭐      |
| **컨텍스트 이해**  | 매우 우수  | 우수           | 우수          |
| **무료 티어**      | 제한적     | 제한적         | 관대함        |
| **응답 속도**      | 빠름       | 빠름           | 매우 빠름     |
| **가격 (1M 토큰)** | $3 (입력)  | $2.5 (입력)    | 무료 (제한적) |

**권장 사항:**

- 품질 우선: Claude (기본값)
- 비용 최적화: Gemini
- 범용성: OpenAI ChatGPT

## 테스트

### 로컬 테스트 실행

가상환경 활성화 후 다음 명령어로 테스트를 실행합니다:

```bash
source venv/bin/activate

# FastAPI 단위 테스트
python -m unittest tests/test_api_daily.py

# 통합 테스트 (REST API → 주간/월간 파이프라인)
python -m unittest tests/test_integration.py

# 전체 테스트 실행
python -m unittest discover -s tests
```

### Docker 환경 통합 테스트

로컬에서 Docker 컨테이너를 실행한 뒤 실제 API 호출로 검증:

```bash
# 1. Docker 빌드 및 실행
docker build -t work-logging-api:local .
docker run --env-file config/.env -p 8000:8000 work-logging-api:local

# 2. 별도 터미널에서 curl 테스트
curl -X GET http://localhost:8000/health
curl -X POST http://localhost:8000/daily-logs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @tests/fixtures/sample_daily_log.json
```

## 운영 및 모니터링

### 1. 사전 준비

1. **Terraform CLI 1.5 이상 설치**
2. **AWS 자격 증명 준비** (`aws configure`)
3. **SSM Parameter Store에 API 키 저장** (SecureString)

```bash
# Notion API 키 저장
aws ssm put-parameter \
  --name "/work-logging/notion_api_key" \
  --value "ntn-your-api-key" \
  --type SecureString

# API 인증 토큰 저장
aws ssm put-parameter \
  --name "/work-logging/api_auth_token" \
  --value "your-bearer-token" \
  --type SecureString
```

### 2. Docker 이미지 빌드 및 ECR 업로드

```bash
# ECR 리포지토리 생성 (최초 1회)
aws ecr create-repository --repository-name work-logging-system/api --region ap-northeast-2

# Docker 이미지 빌드
docker build -t work-logging-api:local .

# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com

# 이미지 태그 및 푸시
docker tag work-logging-api:local <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/work-logging-system/api:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/work-logging-system/api:latest
```

### 3. Terraform 배포

```bash
cd infra/terraform/environments/dev

# terraform.tfvars 파일 생성 (terraform.tfvars.example 참고)
cp terraform.tfvars.example terraform.tfvars
# 편집기로 docker_image_uri, notion_db_ids, ssm_parameter 이름 입력

# Terraform 초기화 및 배포
terraform init -backend-config="../../backends/dev.hcl"
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

배포 완료 후 출력되는 `api_endpoint_url`로 API에 접근할 수 있습니다.

### 4. GitHub Actions 자동 배포 (선택)

`.github/workflows/deploy.yml`을 통해 자동 배포 가능:

1. GitHub Secrets에 AWS 자격 증명 저장 (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Actions 탭에서 `Deploy Infrastructure` 워크플로우 수동 실행
3. Docker 이미지 빌드 → ECR 푸시 → Terraform apply 자동 진행

자세한 내용은 [`deploy/terraform.md`](deploy/terraform.md)를 참고하세요.

## Render 배포 (가장 간편한 방법)

Render는 GitHub 저장소만 연결하면 자동으로 빌드·배포·운영해주는 PaaS 플랫폼입니다. AWS보다 훨씬 간단하게 서비스를 배포할 수 있습니다.

### 장점

- **극도로 간편함**: GitHub 리포지토리 연결만으로 자동 배포
- **무료 플랜**: 월 750시간 무료 (24/7 운영 가능)
- **자동 HTTPS**: SSL 인증서 자동 발급 및 갱신
- **Git 푸시 자동 배포**: main 브랜치에 푸시하면 자동으로 재배포

### 단점

- **Sleep 모드**: 15분 미사용 시 자동으로 sleep (첫 요청 시 20-30초 지연)
- **제한된 리소스**: 무료 플랜은 512MB RAM, 0.1 CPU

### 배포 단계

#### 1. Render 계정 생성 및 GitHub 연결

1. https://render.com 접속 후 GitHub으로 로그인
2. 대시보드에서 `New +` → `Blueprint` 선택
3. 이 저장소를 연결

#### 2. 환경 변수 설정

Render 대시보드에서 서비스 선택 → `Environment` 탭에서 다음 변수를 추가:

```bash
# 필수 환경 변수
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DB1_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DB2_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DB3_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API_AUTH_TOKEN=your_secure_token

# LLM 설정 (선택한 제공자만 설정)
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 3. 배포 확인

1. Render가 자동으로 Docker 이미지를 빌드하고 배포합니다
2. 배포 완료 후 할당된 URL 확인 (예: `https://work-logging-api.onrender.com`)
3. Health check: `https://your-app.onrender.com/health`

#### 4. Sleep 모드 방지 (선택사항)

무료 플랜의 Sleep 모드를 방지하려면 GitHub Actions로 주기적으로 health check를 보내세요.

1. GitHub 저장소 → `Settings` → `Secrets and variables` → `Actions`
2. New repository secret 추가:

   - Name: `RENDER_SERVICE_URL`
   - Value: `https://your-app.onrender.com` (Render에서 할당받은 URL)

3. `.github/workflows/keepalive.yml`이 자동으로 10분마다 `/health`를 호출합니다

**주의:** GitHub Actions도 무료 플랜에서 월 2,000분 제한이 있습니다. 10분마다 실행 시 월 약 4,320분 사용 예상이므로, 필요에 따라 cron 주기를 조정하세요 (예: `*/14 * * * *`로 변경).

#### 5. 대안: 외부 Cron 서비스

GitHub Actions 대신 무료 외부 서비스를 사용할 수도 있습니다:

- **Cron-job.org**: https://cron-job.org
- **UptimeRobot**: https://uptimerobot.com (5분마다 무료)
- **BetterUptime**: https://betteruptime.com

설정 방법:

1. 서비스 가입 후 새 모니터 생성
2. URL: `https://your-app.onrender.com/health`
3. 체크 주기: 10-14분

### Render vs AWS 비교

| 항목            | Render (무료)      | AWS Lambda            |
| --------------- | ------------------ | --------------------- |
| **설정 복잡도** | 매우 쉬움          | 중간 (Terraform 필요) |
| **배포 시간**   | 5분                | 30분+                 |
| **Cold Start**  | 20-30초 (sleep 시) | 1-3초                 |
| **비용**        | $0 (750시간/월)    | $0 (100만 요청/월)    |
| **확장성**      | 제한적             | 무제한                |
| **적합한 사용** | 개인 프로젝트, MVP | 프로덕션, 대규모      |

**권장 사항:**

- 개인 프로젝트, 빠른 프로토타입: Render
- 프로덕션, 고트래픽: AWS Lambda

### Render 배포 문제 해결

**Q: 빌드가 실패합니다**

- Dockerfile이 올바른지 확인
- 로컬에서 `docker build -t test .`로 테스트

**Q: 서비스가 시작되지 않습니다**

- 환경 변수가 모두 설정되었는지 확인
- Render 로그에서 에러 메시지 확인

**Q: API 호출이 401 오류를 반환합니다**

- `API_AUTH_TOKEN`이 올바르게 설정되었는지 확인
- `Authorization: Bearer <token>` 헤더가 정확한지 확인

## 운영 및 모니터링

### Render 대시보드

- https://dashboard.render.com 에서 서비스 상태 확인
- **Logs** 탭: 실시간 API 요청/응답 로그
- **Metrics** 탭: CPU, 메모리 사용량
- **Environment** 탭: 환경 변수 관리

### 비용 모니터링

**Render (무료 플랜):**

- 월 750시간 무료 (24/7 운영 가능)
- 대시보드 → Usage에서 사용량 확인

**LLM API:**

- Claude: https://console.anthropic.com/settings/usage
- OpenAI: https://platform.openai.com/usage
- Gemini: https://aistudio.google.com/app/apikey

### 문제 해결

**API 호출 시 401 오류:**

- Render 환경 변수에 `API_AUTH_TOKEN`이 올바르게 설정되었는지 확인

**서비스가 응답하지 않음:**

- Render 로그에서 에러 메시지 확인
- 배포가 실패했다면 재배포 시도 (Manual Deploy)

**자세한 운영 가이드:**

- [`docs/operations.md`](docs/operations.md) 참고

## 로컬 개발 환경

로컬에서 개발하거나 테스트할 때 사용하는 방법입니다.

### 가상환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-username/work-logging-system.git
cd work-logging-system

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 환경 변수 구성

```bash
# .env 파일 생성
cp config/notion.env.example .env

# .env 파일 편집 (Notion API 키, DB ID 등 입력)
```

### Docker 실행

```bash
# Docker 이미지 빌드
docker build -t work-logging-api:local .

# 컨테이너 실행
docker run --env-file .env -p 8000:8000 work-logging-api:local

# 테스트
curl http://localhost:8000/health
```

### 테스트

```bash
# 전체 테스트 실행
python -m unittest discover -s tests

# 특정 테스트만 실행
python -m unittest tests/test_api_daily.py
```

### 로컬 스크립트 실행

**일간 로그 (CLI):**

```bash
python scripts/daily_logger.py
```

**주간/월간 요약:**

```bash
# 주간 요약 (dry-run)
python scripts/weekly_processor.py --dry-run

# 월간 요약
python scripts/monthly_processor.py --month 2025-11
```

## 고급 배포 옵션

Render 외에 다른 배포 방식도 지원합니다.

### AWS Lambda 배포

프로덕션 환경이나 대규모 트래픽 처리가 필요한 경우 AWS Lambda를 사용할 수 있습니다.

**장점:**

- 무제한 확장성
- Cold start 1-3초 (Render 대비 빠름)
- 프리티어: 월 100만 요청 무료

**단점:**

- 설정 복잡도 높음 (Terraform 필요)
- AWS 계정 및 권한 설정 필요

**배포 가이드:**

자세한 내용은 [`deploy/terraform.md`](deploy/terraform.md)를 참고하세요.

간략한 단계:

1. AWS CLI 설정 및 ECR 리포지토리 생성
2. Docker 이미지 빌드 및 푸시
3. Terraform으로 인프라 구성 (Lambda, API Gateway, SSM)
4. GitHub Actions로 CI/CD 자동화 (선택)

### 자체 서버 배포

Docker가 설치된 자체 서버에서 운영할 수도 있습니다.

```bash
# Docker Compose 사용 예시
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

**권장 사항:**

- 개인 프로젝트/MVP: Render (무료, 간편)
- 프로덕션/대규모: AWS Lambda
- 자체 인프라 보유: Docker 직접 운영
