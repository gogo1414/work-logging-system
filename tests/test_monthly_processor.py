import unittest
from datetime import datetime
from unittest.mock import MagicMock

from scripts.monthly_processor import MonthlyProcessor


class MonthlyProcessorTestCase(unittest.TestCase):
    """MonthlyProcessor 동작을 검증하는 테스트 케이스"""

    def setUp(self):
        self.start_date = datetime(2025, 11, 1)
        self.end_date = datetime(2025, 11, 30)
        self.mock_notion = MagicMock()
        self.mock_claude = MagicMock()
        self.processor = MonthlyProcessor(
            notion_client=self.mock_notion, claude_client=self.mock_claude
        )

    def test_run_with_no_weekly_data(self):
        """주간 성과가 없을 때 Claude 호출 없이 종료되는지 확인"""
        self.mock_notion.get_weekly_achievements_with_content.return_value = []

        result = self.processor.run(
            start_date=self.start_date,
            end_date=self.end_date,
            year=2025,
            month=11,
            dry_run=False,
        )

        self.assertIsNone(result)
        self.mock_claude.generate_monthly_summary.assert_not_called()
        self.mock_notion.create_monthly_highlight.assert_not_called()

    def test_run_with_dry_run(self):
        """Dry-run 모드에서 Notion 저장을 생략하는지 확인"""
        weekly_data = [
            {
                "id": "week-001",
                "properties": {
                    "Source Logs": {"relation": [{"id": "page-1"}, {"id": "page-2"}]}
                },
                "content": "주간 요약 본문",
            }
        ]
        summary_result = {
            "summary": "월간 성과 요약",
            "career_brief": "경력기술서 요약",
            "raw_response": "원문",
        }

        self.mock_notion.get_weekly_achievements_with_content.return_value = weekly_data
        self.mock_claude.generate_monthly_summary.return_value = summary_result

        result = self.processor.run(
            start_date=self.start_date,
            end_date=self.end_date,
            year=2025,
            month=11,
            dry_run=True,
        )

        self.assertEqual(result, summary_result)
        self.mock_notion.create_monthly_highlight.assert_not_called()

    def test_run_with_persist(self):
        """정상 실행 시 Notion에 월간 하이라이트가 저장되는지 확인"""
        weekly_data = [
            {
                "id": "week-001",
                "properties": {
                    "Source Logs": {"relation": [{"id": "page-1"}, {"id": "page-2"}]}
                },
                "content": "주간 요약 본문",
            },
            {
                "id": "week-002",
                "properties": {"Source Logs": {"relation": [{"id": "page-3"}]}},
                "content": "주간 요약 본문 2",
            },
        ]
        summary_result = {
            "summary": "월간 성과 요약",
            "career_brief": "경력기술서 요약",
            "raw_response": "원문",
        }

        self.mock_notion.get_weekly_achievements_with_content.return_value = weekly_data
        self.mock_claude.generate_monthly_summary.return_value = summary_result
        self.mock_notion.create_monthly_highlight.return_value = {"id": "monthly-001"}

        result = self.processor.run(
            start_date=self.start_date,
            end_date=self.end_date,
            year=2025,
            month=11,
            dry_run=False,
        )

        self.assertEqual(result, {"id": "monthly-001"})
        self.mock_notion.create_monthly_highlight.assert_called_once()
        call_kwargs = self.mock_notion.create_monthly_highlight.call_args.kwargs
        self.assertEqual(call_kwargs["year"], 2025)
        self.assertEqual(call_kwargs["month"], 11)
        self.assertEqual(call_kwargs["source_week_ids"], ["week-001", "week-002"])
        self.assertIn("총 주간 성과 수: 2개", call_kwargs["stats_text"])


if __name__ == "__main__":
    unittest.main()
