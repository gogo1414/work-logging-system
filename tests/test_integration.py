import os
import unittest
import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from scripts.api.app import app, get_notion_client
from scripts.monthly_processor import MonthlyProcessor
from scripts.weekly_processor import WeeklyProcessor


class _InMemoryStore:
    """테스트 간 공유되는 인메모리 저장소"""

    def __init__(self):
        self.daily: list[dict] = []
        self.weekly: list[dict] = []
        self.monthly: list[dict] = []

    def reset(self):
        self.daily.clear()
        self.weekly.clear()
        self.monthly.clear()


class _StubNotionClient:
    """통합 테스트용 Notion 래퍼 스텁"""

    def __init__(self, store: _InMemoryStore):
        self.store = store

    # --- Daily ---
    def create_daily_log(
        self,
        title: str,
        context: str,
        category: str,
        impact_level: str,
        tech_stack: list[str],
        logged_date: datetime | None = None,
        status: str | None = None,
        metrics: str | None = None,
        ticket_url: str | None = None,
    ) -> dict:
        page_id = str(uuid.uuid4())
        entry = {
            "id": page_id,
            "logged_date": (logged_date or datetime.now()).date(),
            "properties": {
                "Title": {"title": [{"text": {"content": title}}]},
                "Category": {"select": {"name": category}},
                "Impact Level": {"select": {"name": impact_level}},
                "Tech Stack": {"multi_select": [{"name": tech} for tech in tech_stack]},
                "Metrics": {"rich_text": ([{"text": {"content": metrics}}] if metrics else [])},
            },
            "content": context,
        }
        self.store.daily.append(entry)
        return entry

    def get_daily_logs_with_content(
        self,
        start_date: datetime,
        end_date: datetime,
        status_filter: str | None = None,
    ) -> list[dict]:
        return [
            entry
            for entry in self.store.daily
            if start_date.date() <= entry["logged_date"] <= end_date.date()
        ]

    # --- Weekly ---
    def create_weekly_achievement(
        self,
        period_start: datetime,
        period_end: datetime,
        bullet_points: str,
        key_highlights: str,
        source_log_ids: list[str],
    ) -> dict:
        page_id = str(uuid.uuid4())
        entry = {
            "id": page_id,
            "period_start": period_start.date(),
            "period_end": period_end.date(),
            "properties": {
                "Title": {"title": [{"text": {"content": f"{period_start:%Y년 %m월 %W주차}"}}]},
                "Key Highlights": {"rich_text": [{"text": {"content": key_highlights}}]},
                "Source Logs": {"relation": [{"id": log_id} for log_id in source_log_ids]},
            },
            "content": bullet_points,
        }
        self.store.weekly.append(entry)
        return entry

    def get_weekly_achievements_with_content(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        return [
            entry
            for entry in self.store.weekly
            if start_date.date() <= entry["period_start"] <= end_date.date()
        ]

    # --- Monthly ---
    def create_monthly_highlight(
        self,
        year: int,
        month: int,
        summary: str,
        career_brief: str,
        source_week_ids: list[str],
        stats_text: str,
    ) -> dict:
        page_id = str(uuid.uuid4())
        entry = {
            "id": page_id,
            "properties": {
                "Title": {"title": [{"text": {"content": f"{year}년 {month:02d}월"}}]},
                "Stats": {"rich_text": [{"text": {"content": stats_text}}]},
                "Source Weeks": {"relation": [{"id": week_id} for week_id in source_week_ids]},
            },
            "content": {"summary": summary, "career_brief": career_brief},
        }
        self.store.monthly.append(entry)
        return entry


class _StubClaudeWeeklyClient:
    """주간 요약을 고정 응답으로 반환하는 스텁"""

    def generate_weekly_summary(self, daily_logs, system_prompt=None):
        return {
            "bullet_points": (
                "• ### Situation\n"
                "  일일 로그가 CLI 수동 입력에만 의존해 자동 기록이 불가능했습니다.\n"
                "  ### Task\n"
                "  FastAPI 기반 REST API를 서버리스 환경에 배포하고 비용을 최소화해야 했습니다.\n"
                "  ### Action\n"
                "  Docker 이미지, AWS Lambda+API Gateway, Terraform 모듈, 통합 테스트 10건을 구성했습니다.\n"
                "  ### Result\n"
                "  Notion 자동 기록 도입, 회귀 테스트 자동화, 운영 비용 0원 유지로 업무 생산성 향상"
            ),
            "key_highlights": (
                "### Situation\n"
                "CLI 중심 로그 관리로 업무 이력 자동화가 미흡했습니다.\n"
                "### Task\n"
                "REST API와 서버리스 인프라로 자동 기록 체계를 마련해야 했습니다.\n"
                "### Action\n"
                "FastAPI+Doker+Terraform 구성으로 Lambda 배포 및 통합 테스트 작성\n"
                "### Result\n"
                "Notion 자동 기록, 테스트 10건 자동화, 운영 비용 무증가"
            ),
            "raw_response": "stub-weekly",
        }


class _StubClaudeMonthlyClient:
    """월간 요약을 고정 응답으로 반환하는 스텁"""

    def generate_monthly_summary(self, weekly_achievements, system_prompt=None):
        return {
            "summary": (
                "## 월간 종합 성과\n"
                "### Situation\n"
                "수동 로그로 업무 히스토리가 누락되며 노션과 이력 관리가 지연되고 있었습니다.\n"
                "### Task\n"
                "REST API, 서버리스 인프라, 통합 테스트를 갖춘 자동 기록 파이프라인을 구축해야 했습니다.\n"
                "### Action\n"
                "FastAPI 컨테이너, AWS Lambda+API Gateway, Terraform 모듈, 테스트 10건을 설계했습니다.\n"
                "### Result\n"
                "Notion 자동 기록 도입, 회귀 테스트 자동화, 운영 비용 0원 유지로 월간 업무 가시성 확보\n"
                "### Situation\n"
                "LLM 요약이 구조 없이 출력돼 이력서 활용이 어려웠습니다.\n"
                "### Task\n"
                "STAR 구조를 강제하는 프롬프트와 검증 데이터를 마련해야 했습니다.\n"
                "### Action\n"
                "주간/월간 프롬프트를 STAR 형식으로 개편하고 테스트 데이터를 업데이트했습니다.\n"
                "### Result\n"
                "자동 요약 품질 향상, 이력서 전환 시간 50% 단축, 프롬프트 일관성 확보"
            ),
            "career_brief": (
                "• REST API+Lambda+Terraform으로 Notion 자동 기록 파이프라인 구축, 운영 비용 0원 유지\n"
                "• STAR 프롬프트 개편과 통합 테스트 10건 자동화로 로그→이력서 전환 속도 50% 단축"
            ),
            "raw_response": "stub-monthly",
        }


class IntegrationFlowTestCase(unittest.TestCase):
    """일간 → 주간 → 월간 파이프라인 통합 테스트"""

    def setUp(self):
        self.store = _InMemoryStore()
        self.stub_notion = _StubNotionClient(self.store)
        app.dependency_overrides[get_notion_client] = lambda: self.stub_notion
        os.environ["API_AUTH_TOKEN"] = "integration-token"
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        os.environ.pop("API_AUTH_TOKEN", None)
        self.store.reset()

    def test_api_to_monthly_flow(self):
        payload = {
            "title": "Lambda 기반 REST API 배포",
            "context": (
                "### Situation\n"
                "일일 로그를 수동으로만 작성해 Notion에 적시에 기록되지 않았습니다.\n\n"
                "### Task\n"
                "REST API를 만들어 Docker와 AWS Lambda에 배포하고 자동 기록을 보장해야 했습니다.\n\n"
                "### Action\n"
                "- FastAPI `/daily-logs` 엔드포인트 구현 및 Bearer 인증 적용\n"
                "- Docker 이미지 빌드, Terraform으로 Lambda+API Gateway 구성\n"
                "- 통합 테스트와 문서화로 파이프라인 품질 확보\n\n"
                "### Result\n"
                "Notion 자동 기록 가능, 테스트 10건 통과, 비용 증가 없이 서버리스 운영"
            ),
            "category": "신규기능",
            "impact_level": "High",
            "tech_stack": ["Python", "FastAPI", "AWS Lambda"],
            "logged_date": "2025-11-09",
            "metrics": "REST API 기반 자동 기록 도입",
        }

        response = self.client.post(
            "/daily-logs",
            json=payload,
            headers={"Authorization": "Bearer integration-token"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.store.daily), 1)

        start_date = datetime(2025, 11, 8)
        end_date = datetime(2025, 11, 10)

        weekly_processor = WeeklyProcessor(
            notion_client=self.stub_notion,
            claude_client=_StubClaudeWeeklyClient(),
        )
        weekly_processor.run(
            start_date=start_date,
            end_date=end_date,
            status_filter=None,
            dry_run=False,
        )
        self.assertEqual(len(self.store.weekly), 1)

        monthly_processor = MonthlyProcessor(
            notion_client=self.stub_notion,
            claude_client=_StubClaudeMonthlyClient(),
        )
        monthly_processor.run(
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 30),
            year=2025,
            month=11,
            dry_run=False,
        )

        self.assertEqual(len(self.store.monthly), 1)
        monthly_entry = self.store.monthly[0]
        self.assertIn("summary", monthly_entry["content"])
        self.assertEqual(
            monthly_entry["content"]["career_brief"],
            "• REST API+Lambda+Terraform으로 Notion 자동 기록 파이프라인 구축, 운영 비용 0원 유지\n"
            "• STAR 프롬프트 개편과 통합 테스트 10건 자동화로 로그→이력서 전환 속도 50% 단축",
        )


if __name__ == "__main__":
    unittest.main()
