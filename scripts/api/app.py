"""
일일 업무 기록을 REST API로 제공하는 FastAPI 애플리케이션
"""

import os
from datetime import datetime

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from scripts.utils.notion_client import NotionClientWrapper

app = FastAPI(
    title="Work Logging API",
    summary="Cursor/Claude와 연동해 Notion Daily Work Logs를 생성하는 REST API",
    version="1.0.0",
)


class DailyLogRequest(BaseModel):
    """일일 업무 로그 생성을 위한 요청 본문"""

    title: str = Field(..., description="업무 제목 (한 줄 요약)")
    context: str = Field(..., description="문제/해결/결과를 포함한 상세 컨텍스트")
    category: str = Field(..., description="업무 카테고리 (성능개선, 신규기능 등)")
    impact_level: str = Field(..., description="영향도 (High/Medium/Low)")
    tech_stack: list[str] = Field(..., description="사용 기술 스택 목록")
    logged_date: str | None = Field(
        None, description="기록 일자 (YYYY-MM-DD), 미지정 시 오늘 날짜"
    )
    status: str | None = Field(
        default="Logged", description="초기 상태 (기본값 Logged)"
    )
    metrics: str | None = Field(None, description="정량 지표 (예: 응답시간 50% 단축)")
    ticket_url: str | None = Field(None, description="관련 이슈 URL (Jira, GitHub 등)")

    @validator("logged_date")
    def validate_logged_date(cls, value: str | None) -> str | None:
        """YYYY-MM-DD 형식 검증"""
        if value is None:
            return value
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("logged_date는 YYYY-MM-DD 형식이어야 합니다.") from exc
        return value


class DailyLogResponse(BaseModel):
    """노션 페이지 생성 결과 응답"""

    page_id: str = Field(..., description="생성된 Notion 페이지 ID")
    url: str = Field(..., description="생성된 Notion 페이지 URL")


def write_execution_log(status_text: str, message: str):
    """API 처리 결과를 로그 파일에 남김"""
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "execution.log")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] [{status_text}] api_server - {message}\n")


def get_auth_token() -> str | None:
    """환경 변수에서 API 토큰을 읽어옴"""
    return os.getenv("API_AUTH_TOKEN")


def get_notion_client() -> NotionClientWrapper:
    """요청마다 Notion 클라이언트를 생성"""
    return NotionClientWrapper()


async def verify_token(
    authorization: str | None = Header(default=None),
    token_value: str | None = Depends(get_auth_token),
) -> None:
    """
    Authorization 헤더 검증

    API_AUTH_TOKEN이 설정되지 않았다면 인증을 건너뛰고,
    설정되어 있다면 Bearer 토큰을 비교한다.
    """
    if not token_value:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효한 Authorization 헤더가 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request_token = authorization.split(" ", 1)[1].strip()
    if request_token != token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 일치하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """배포 상태 확인용 엔드포인트"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post(
    "/daily-logs",
    response_model=DailyLogResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Daily Logs"],
)
async def create_daily_log(
    payload: DailyLogRequest,
    _: None = Depends(verify_token),
    notion: NotionClientWrapper = Depends(get_notion_client),
) -> JSONResponse:
    """일일 업무 로그를 Notion 데이터베이스에 저장"""
    try:
        logged_date = (
            datetime.strptime(payload.logged_date, "%Y-%m-%d")
            if payload.logged_date
            else datetime.now()
        )

        page = notion.create_daily_log(
            title=payload.title,
            context=payload.context,
            category=payload.category,
            impact_level=payload.impact_level,
            tech_stack=payload.tech_stack,
            logged_date=logged_date,
            status=payload.status,
            metrics=payload.metrics,
            ticket_url=payload.ticket_url,
        )

        page_id = page.get("id")
        notion_url = f"https://notion.so/{page_id.replace('-', '')}" if page_id else ""

        write_execution_log("SUCCESS", f"API로 일일 로그 생성: {page_id}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=DailyLogResponse(page_id=page_id, url=notion_url).dict(),
        )
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        write_execution_log("ERROR", f"API 처리 실패: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="노션 저장 중 오류가 발생했습니다.",
        ) from exc
