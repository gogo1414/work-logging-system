import unittest
from datetime import datetime
from unittest.mock import MagicMock

from scripts.weekly_processor import WeeklyProcessor


class WeeklyProcessorTestCase(unittest.TestCase):
    """WeeklyProcessor 동작을 검증하는 테스트 케이스"""

    def setUp(self):
        self.start_date = datetime(2025, 11, 3)
        self.end_date = datetime(2025, 11, 9)
        self.mock_notion = MagicMock()
        self.mock_claude = MagicMock()
        self.processor = WeeklyProcessor(
            notion_client=self.mock_notion, claude_client=self.mock_claude
        )

    def test_run_with_no_logs(self):
        """일일 로그가 없을 때 Claude 호출 없이 종료되는지 확인"""
        self.mock_notion.get_daily_logs_with_content.return_value = []

        result = self.processor.run(
            start_date=self.start_date, end_date=self.end_date, status_filter=None, dry_run=False
        )

        self.assertIsNone(result)
        self.mock_claude.generate_weekly_summary.assert_not_called()
        self.mock_notion.create_weekly_achievement.assert_not_called()

    def test_run_with_dry_run(self):
        """Dry-run 모드에서 Notion 저장을 생략하는지 확인"""
        sample_logs = [{"id": "page-123", "content": "상세 내용"}]
        summary_result = {
            "bullet_points": "• 샘플 불릿",
            "key_highlights": "핵심 임팩트",
            "raw_response": "원문",
        }

        self.mock_notion.get_daily_logs_with_content.return_value = sample_logs
        self.mock_claude.generate_weekly_summary.return_value = summary_result

        result = self.processor.run(
            start_date=self.start_date, end_date=self.end_date, status_filter=None, dry_run=True
        )

        self.assertEqual(result, summary_result)
        self.mock_notion.create_weekly_achievement.assert_not_called()

    def test_run_with_persist(self):
        """정상 실행 시 Notion에 주간 성과가 저장되는지 확인"""
        sample_logs = [{"id": "page-123", "content": "상세 내용"}]
        summary_result = {
            "bullet_points": "• 샘플 불릿",
            "key_highlights": "핵심 임팩트",
            "raw_response": "원문",
        }

        self.mock_notion.get_daily_logs_with_content.return_value = sample_logs
        self.mock_claude.generate_weekly_summary.return_value = summary_result
        self.mock_notion.create_weekly_achievement.return_value = {"id": "weekly-001"}

        result = self.processor.run(
            start_date=self.start_date,
            end_date=self.end_date,
            status_filter="Logged",
            dry_run=False,
        )

        self.assertEqual(result, {"id": "weekly-001"})
        self.mock_notion.create_weekly_achievement.assert_called_once_with(
            period_start=self.start_date,
            period_end=self.end_date,
            bullet_points="• 샘플 불릿",
            key_highlights="핵심 임팩트",
            source_log_ids=["page-123"],
        )


if __name__ == "__main__":
    unittest.main()
