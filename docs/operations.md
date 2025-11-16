# 운영 가이드

이 문서는 work-logging-system의 운영, 모니터링, 문제 해결 가이드를 제공합니다.

## 목차

- [배포 환경 개요](#배포-환경-개요)
- [Render 운영](#render-운영)
- [AWS Lambda 운영](#aws-lambda-운영)
- [로그 및 모니터링](#로그-및-모니터링)
- [문제 해결](#문제-해결)
- [정기 점검](#정기-점검)

## 배포 환경 개요

### 지원하는 배포 환경

1. **Render (PaaS)** - 개인 프로젝트, 빠른 프로토타입에 적합
2. **AWS Lambda (Serverless)** - 프로덕션, 대규모 트래픽에 적합
3. **로컬 Docker** - 개발 및 테스트

## Render 운영

### 기본 모니터링

**대시보드 접속:**

1. https://dashboard.render.com 로그인
2. 서비스 목록에서 `work-logging-api` 선택

**확인 항목:**

- **Status**: 서비스가 `Live` 상태인지 확인
- **Last Deploy**: 최근 배포 시간
- **Metrics**: CPU, Memory 사용률
- **Logs**: 실시간 로그 스트림

### Sleep 모드 관리

**Sleep 상태 확인:**

```bash
curl https://your-app.onrender.com/health
```

- 응답이 즉시 오면: Active 상태
- 20-30초 후 응답: Sleep에서 깨어나는 중
- 응답 없음: 서비스 장애

**Keep-alive 설정 확인:**

1. GitHub Actions 워크플로우 상태 확인:

   - GitHub 저장소 → `Actions` 탭
   - `Keep Render Service Alive` 워크플로우 실행 이력 확인

2. 워크플로우가 실패하는 경우:
   - `Settings` → `Secrets and variables` → `Actions`
   - `RENDER_SERVICE_URL`이 올바른지 확인

**대안: UptimeRobot 사용**

GitHub Actions 제한을 피하고 싶다면:

1. https://uptimerobot.com 가입 (무료)
2. `Add New Monitor` 클릭
   - Monitor Type: HTTP(s)
   - Friendly Name: Work Logging API
   - URL: `https://your-app.onrender.com/health`
   - Monitoring Interval: 5분
3. Alert Contacts 설정 (선택)

### 환경 변수 관리

**환경 변수 변경:**

1. Render 대시보드 → 서비스 선택
2. `Environment` 탭
3. 변경할 변수 편집 후 `Save Changes`
4. 자동으로 재배포됨

**중요한 환경 변수:**

```bash
# API 인증 (선택사항, 미설정 시 인증 없음)
API_AUTH_TOKEN=your_secure_token

# LLM 제공자
LLM_PROVIDER=claude  # claude | openai | gemini

# Notion 설정
NOTION_API_KEY=secret_xxx...
NOTION_DB1_ID=xxx...
NOTION_DB2_ID=xxx...
NOTION_DB3_ID=xxx...

# LLM API 키 (사용하는 제공자만 설정)
CLAUDE_API_KEY=sk-ant-xxx...
OPENAI_API_KEY=sk-xxx...
GEMINI_API_KEY=xxx...
```

### 로그 확인

**실시간 로그:**

1. Render 대시보드 → 서비스 선택
2. `Logs` 탭
3. 필터 옵션:
   - `All Logs`: 모든 로그
   - `Deploy Logs`: 배포 로그만
   - `Runtime Logs`: 애플리케이션 로그만

**로그 검색:**

- Ctrl+F (또는 Cmd+F)로 키워드 검색
- 예: "ERROR", "SUCCESS", "401"

**로그 다운로드:**

- 로그 화면 우측 상단 `Download Logs` 클릭

### 배포 관리

**수동 재배포:**

1. Render 대시보드 → 서비스 선택
2. `Manual Deploy` → `Deploy latest commit` 클릭

**자동 배포 비활성화:**

1. 서비스 설정 → `Settings` 탭
2. `Auto-Deploy` 토글 OFF

**롤백:**

1. `Deploy` 탭에서 이전 배포 선택
2. `Rollback to this version` 클릭

### 비용 모니터링

**무료 플랜 제한:**

- 월 750시간 (24/7 운영 시 약 31일)
- 512MB RAM
- 0.1 CPU
- 100GB 대역폭

**사용량 확인:**

1. Render 대시보드 → `Account Settings`
2. `Usage` 탭에서 현재 사용량 확인

**유료 플랜 고려 시점:**

- Sleep 모드가 문제가 되는 경우
- 동시 사용자 증가로 성능 저하 발생
- 월 트래픽이 100GB 초과

## AWS Lambda 운영

### CloudWatch Logs 확인

**로그 그룹 접속:**

```bash
# AWS CLI로 최근 로그 확인
aws logs tail /aws/lambda/work-logging-api-dev --follow

# 또는 AWS Console에서
# CloudWatch → Log groups → /aws/lambda/work-logging-api-dev
```

**필터 패턴 예시:**

- 에러만: `?ERROR ?Exception ?Traceback`
- 특정 API: `?"POST /daily-logs"`
- 성공 요청: `?201 ?Created`

### 비용 추적

**예상 비용:**

- Lambda: $0.20 per 1M requests
- API Gateway: $3.50 per 1M requests
- CloudWatch Logs: $0.50 per GB ingested

**월 비용 확인:**

```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-30 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://filter.json
```

## 로그 및 모니터링

### LLM API 사용량 모니터링

**Claude (Anthropic):**

- https://console.anthropic.com/settings/usage
- 일별/월별 토큰 사용량 확인

**OpenAI (ChatGPT):**

- https://platform.openai.com/usage
- API 키별 사용량 및 비용 확인

**Google (Gemini):**

- https://aistudio.google.com/app/apikey
- 무료 티어 할당량 확인

### Notion API 제한

**Rate Limit:**

- 초당 3 requests (평균)
- 짧은 버스트: 초당 최대 10 requests

**제한 초과 시 대응:**

- 429 에러 발생 시 자동 재시도 (exponential backoff)
- 로그에서 `rate_limit_exceeded` 키워드 검색

### 애플리케이션 로그

**로컬 환경:**

```bash
# 실행 로그 확인
tail -f logs/execution.log

# 특정 모듈만 필터링
grep "weekly_processor" logs/execution.log
grep "ERROR" logs/execution.log
```

**로그 레벨:**

- `INFO`: 일반 정보
- `SUCCESS`: 작업 성공
- `ERROR`: 오류 발생
- `CANCELLED`: 사용자 중단

## 문제 해결

### 자주 발생하는 문제

#### 1. API 호출 시 401 Unauthorized

**원인:**

- `API_AUTH_TOKEN` 미설정 또는 불일치
- Authorization 헤더 누락

**해결:**

```bash
# 환경 변수 확인
echo $API_AUTH_TOKEN

# 올바른 요청 형식
curl -X POST https://your-api/daily-logs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @request.json
```

#### 2. LLM API 호출 실패

**원인:**

- API 키 누락 또는 잘못됨
- 할당량 초과
- 네트워크 오류

**해결:**

```bash
# 환경 변수 확인
echo $LLM_PROVIDER
echo $CLAUDE_API_KEY  # 또는 OPENAI_API_KEY, GEMINI_API_KEY

# LLM 제공자 변경 시도
export LLM_PROVIDER=gemini
python scripts/weekly_processor.py --dry-run
```

#### 3. Notion API 호출 실패

**원인:**

- API 키 만료
- 데이터베이스 권한 없음
- Rate limit 초과

**해결:**

1. Notion Integration 페이지에서 API 키 확인
2. 데이터베이스 Connections 설정 확인
3. Rate limit 시 1분 대기 후 재시도

#### 4. Render Sleep 모드에서 깨어나지 않음

**원인:**

- 서비스 크래시
- 메모리 부족
- 빌드 실패

**해결:**

1. Render 로그에서 에러 확인
2. 로컬에서 Docker 빌드 테스트
   ```bash
   docker build -t test .
   docker run --env-file .env -p 8000:8000 test
   ```
3. 메모리 사용량 최적화 필요 시 유료 플랜 고려

#### 5. GitHub Actions Keep-alive 실패

**원인:**

- RENDER_SERVICE_URL 미설정
- GitHub Actions 할당량 초과

**해결:**

1. Secret 설정 확인
2. 워크플로우 cron 주기 늘리기 (`*/14 * * * *`)
3. 또는 UptimeRobot 등 외부 서비스 사용

### 디버깅 팁

**로컬에서 재현:**

```bash
# 동일한 환경 변수로 로컬 실행
source venv/bin/activate
python -m scripts.api.app

# 또는 Docker로
docker run --env-file .env -p 8000:8000 work-logging-api:local
```

**상세 로그 활성화:**

```python
# 임시로 더 많은 로그 출력
import logging
logging.basicConfig(level=logging.DEBUG)
```

**API 직접 테스트:**

```bash
# Health check
curl https://your-api/health

# Daily log 생성 (dry-run)
curl -X POST https://your-api/daily-logs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","context":"### Situation\nTest","category":"테스트","impact_level":"Low","tech_stack":["Test"]}'
```

## 정기 점검

### 주간 체크리스트

- [ ] Render/AWS 서비스 상태 확인
- [ ] 에러 로그 검토
- [ ] LLM API 사용량 확인
- [ ] Notion 데이터 정합성 확인

### 월간 체크리스트

- [ ] 비용 리포트 검토
- [ ] 환경 변수 및 API 키 갱신 필요 여부 확인
- [ ] 백업 데이터 점검 (Notion export)
- [ ] 의존성 업데이트 검토 (`requirements.txt`)

### 분기 체크리스트

- [ ] 보안 취약점 점검
- [ ] LLM 모델 버전 업데이트 고려
- [ ] 성능 최적화 검토
- [ ] 문서 업데이트

## 연락처 및 지원

**긴급 장애 발생 시:**

1. 로그 확인 (Render/AWS CloudWatch)
2. GitHub Issues에 문제 보고
3. 필요시 수동으로 Notion 데이터 입력

**유용한 링크:**

- Render Status: https://status.render.com
- AWS Status: https://health.aws.amazon.com/health/status
- Anthropic Status: https://status.anthropic.com
- OpenAI Status: https://status.openai.com
- Notion Status: https://status.notion.so
