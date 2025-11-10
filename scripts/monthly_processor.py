#!/usr/bin/env python3
"""
월간 자동 처리 스크립트: 주간 성과를 모아 Claude로 요약하고 Notion 월간 DB에 기록
"""

import argparse
import calendar
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.utils.claude_client import ClaudeClientWrapper
from scripts.utils.notion_client import NotionClientWrapper


def write_execution_log(status: str, message: str):
    """
    스크립트 실행 결과를 로그 파일에 남김

    Args:
        status: SUCCESS, ERROR 등 상태 문자열
        message: 상태에 대한 상세 설명
    """
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "execution.log")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] [{status}] monthly_processor - {message}\n")


def parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱"""
    parser = argparse.ArgumentParser(
        description="주간 성과를 집계해 Notion Monthly Highlights DB에 저장합니다."
    )
    parser.add_argument("--year", type=int, help="집계 연도 (예: 2025). 미지정 시 현재 연도.")
    parser.add_argument("--month", type=int, help="집계 월 (1-12). 미지정 시 현재 월.")
    parser.add_argument(
        "--start-date",
        dest="start_date",
        type=str,
        help="직접 시작일을 지정하고 싶을 때 사용 (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        dest="end_date",
        type=str,
        help="직접 종료일을 지정하고 싶을 때 사용 (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Notion에 저장하지 않고 콘솔에 결과만 출력.",
    )
    return parser.parse_args()


def resolve_period(
    start_str: str | None, end_str: str | None, year: int | None, month: int | None
) -> tuple[datetime, datetime, int, int]:
    """
    월간 집계 기간을 결정

    우선순위: 명시적 start/end > year/month > 현재 날짜 기준
    """
    if start_str or end_str:
        if not start_str or not end_str:
            raise ValueError("start-date와 end-date는 동시에 지정해야 합니다.")
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        target_year = start_date.year
        target_month = start_date.month
    else:
        today = datetime.now().date()
        target_year = year or today.year
        target_month = month or today.month
        _, last_day = calendar.monthrange(target_year, target_month)
        start_date = datetime(target_year, target_month, 1).date()
        end_date = datetime(target_year, target_month, last_day).date()

    if start_date > end_date:
        raise ValueError("시작일은 종료일보다 이후일 수 없습니다.")

    return (
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.min.time()),
        target_year,
        target_month,
    )


class MonthlyProcessor:
    """월간 자동 요약 및 저장을 담당하는 클래스"""

    def __init__(
        self,
        notion_client: NotionClientWrapper | None = None,
        claude_client: ClaudeClientWrapper | None = None,
    ):
        self.notion = notion_client or NotionClientWrapper()
        self.claude = claude_client or ClaudeClientWrapper()

    def fetch_weekly_achievements(self, start_date: datetime, end_date: datetime) -> list[dict]:
        """월간 기간에 해당하는 주간 성과를 조회"""
        return self.notion.get_weekly_achievements_with_content(start_date, end_date)

    def summarize_weeks(self, weekly_data: list[dict]) -> dict:
        """Claude API로 월간 요약을 생성"""
        return self.claude.generate_monthly_summary(weekly_data)

    def build_stats_text(
        self, weekly_data: list[dict], start_date: datetime, end_date: datetime
    ) -> str:
        """월간 통계 요약 문자열 생성"""
        total_weeks = len(weekly_data)
        total_daily_logs = 0

        for week in weekly_data:
            relation = week.get("properties", {}).get("Source Logs", {}).get("relation", [])
            total_daily_logs += len(relation)

        lines = [
            f"집계 기간: {start_date.date()} ~ {end_date.date()}",
            f"총 주간 성과 수: {total_weeks}개",
            f"연관된 일일 로그 수: {total_daily_logs}개",
        ]
        return "\n".join(lines)

    def save_monthly_summary(
        self, year: int, month: int, summary: dict, weekly_data: list[dict], stats_text: str
    ) -> dict:
        """월간 요약을 Notion 월간 DB에 저장"""
        source_week_ids = [week["id"] for week in weekly_data if "id" in week]
        page = self.notion.create_monthly_highlight(
            year=year,
            month=month,
            summary=summary.get("summary", ""),
            career_brief=summary.get("career_brief", ""),
            source_week_ids=source_week_ids,
            stats_text=stats_text,
        )
        return page

    def run(
        self, start_date: datetime, end_date: datetime, year: int, month: int, dry_run: bool = False
    ) -> dict | None:
        """월간 요약 전체 흐름 실행"""
        write_execution_log("INFO", f"월간 처리 시작: {start_date.date()} ~ {end_date.date()}")

        weekly_data = self.fetch_weekly_achievements(start_date, end_date)
        if not weekly_data:
            write_execution_log("INFO", "집계 기간에 해당하는 주간 성과가 없습니다.")
            return None

        summary = self.summarize_weeks(weekly_data)
        stats_text = self.build_stats_text(weekly_data, start_date, end_date)

        if dry_run:
            write_execution_log("INFO", "Dry-run 모드로 실행됨. Notion 저장을 건너뜁니다.")
            print("## 월간 종합 성과")
            print(summary.get("summary", ""))
            print("\n## 경력기술서용 요약")
            print(summary.get("career_brief", ""))
            print("\n## 통계 요약")
            print(stats_text)
            return summary

        page = self.save_monthly_summary(year, month, summary, weekly_data, stats_text)
        write_execution_log("SUCCESS", f"월간 하이라이트 저장 완료: {page.get('id')}")
        return page


def main():
    """CLI 엔트리 포인트"""
    args = parse_args()

    try:
        start_date, end_date, year, month = resolve_period(
            args.start_date, args.end_date, args.year, args.month
        )
    except ValueError as error:
        write_execution_log("ERROR", f"기간 해석 실패: {error}")
        print(f"기간 설정 오류: {error}")
        sys.exit(1)

    try:
        processor = MonthlyProcessor()
        processor.run(
            start_date=start_date, end_date=end_date, year=year, month=month, dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        write_execution_log("CANCELLED", "사용자가 Ctrl+C로 종료함")
        print("사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as error:
        write_execution_log("ERROR", f"월간 처리 실패: {error}")
        print(f"월간 자동 처리 중 오류가 발생했습니다: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
