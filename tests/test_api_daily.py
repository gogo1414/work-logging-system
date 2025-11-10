import os
import unittest
import uuid

from fastapi.testclient import TestClient

from scripts.api.app import app, get_notion_client


class _StubNotionClient:
    """FastAPI 단위 테스트용 Notion 클라이언트 스텁"""

    def __init__(self):
        self.created_logs: list[dict] = []

    def create_daily_log(
        self,
        title: str,
        context: str,
        category: str,
        impact_level: str,
        tech_stack: list[str],
        logged_date,
        status: str | None = None,
        metrics: str | None = None,
        ticket_url: str | None = None,
    ) -> dict:
        page_id = str(uuid.uuid4())
        entry = {
            "id": page_id,
            "properties": {
                "Title": {"title": [{"text": {"content": title}}]},
            },
            "content": context,
        }
        self.created_logs.append(entry)
        return entry


class DailyLogApiTestCase(unittest.TestCase):
    """일간 REST API 단위 테스트"""

    def setUp(self):
        self.stub_notion = _StubNotionClient()
        app.dependency_overrides[get_notion_client] = lambda: self.stub_notion
        os.environ["API_AUTH_TOKEN"] = "test-token"
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        os.environ.pop("API_AUTH_TOKEN", None)

    def test_create_daily_log_success(self):
        payload = {
            "title": "API 성능 개선",
            "context": "### Situation\n주요 API가 피크 타임에 2초 이상 지연되어 고객 이탈이 발생했습니다.\n\n### Task\n응답 시간을 0.5초 이하로 낮추고, 모니터링 체계를 자동화해야 했습니다.\n\n### Action\n- 로딩 쿼리 프로파일링 후 N+1 문제 제거\n- FastAPI 레이어 캐싱 도입 및 Grafana 알림 설정\n\n### Result\n평균 응답 시간 2.3초→0.23초(90% 개선), SLA 위반 0건, CS 문의 35% 감소",
            "category": "성능개선",
            "impact_level": "High",
            "tech_stack": ["Python", "FastAPI"],
            "logged_date": "2025-11-09",
        }

        response = self.client.post(
            "/daily-logs",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("page_id", response.json())
        self.assertEqual(len(self.stub_notion.created_logs), 1)

    def test_create_daily_log_unauthorized(self):
        payload = {
            "title": "무단 접근 테스트",
            "context": "### Situation\n권한 없이 API 호출을 시도했습니다.\n\n### Task\n인증 없이 접근했을 때 401이 반환되는지 확인합니다.\n\n### Action\nBearer 토큰을 생략해 `/daily-logs` 엔드포인트 요청\n\n### Result\n401 Unauthorized 응답 수신, Notion 호출 없음",
            "category": "기타",
            "impact_level": "Low",
            "tech_stack": ["Python"],
        }

        response = self.client.post("/daily-logs", json=payload)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(self.stub_notion.created_logs), 0)

    def test_create_daily_log_invalid_date(self):
        payload = {
            "title": "잘못된 날짜",
            "context": "### Situation\n잘못된 날짜 형식을 가진 요청을 전송했습니다.\n\n### Task\n입력 검증이 동작하는지 확인합니다.\n\n### Action\n`logged_date`를 `2025/11/09`로 설정해 요청\n\n### Result\n422 Unprocessable Entity 응답을 기대",
            "category": "기타",
            "impact_level": "Low",
            "tech_stack": ["Python"],
            "logged_date": "2025/11/09",
        }

        response = self.client.post(
            "/daily-logs",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(self.stub_notion.created_logs), 0)


if __name__ == "__main__":
    unittest.main()
