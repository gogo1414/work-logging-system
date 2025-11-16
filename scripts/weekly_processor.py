#!/usr/bin/env python3
"""
주간 자동 처리 스크립트: 일일 로그를 모아 Claude로 요약하고 Notion 주간 DB에 기록
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.utils.llm_client import BaseLLMClient, LLMClientFactory
from scripts.utils.notion_client import NotionClientWrapper


def write_execution_log(status: str, message: str):
    """
    스크립트 실행 결과를 로그 파일로 남김

    Args:
        status: SUCCESS, ERROR 등 상태 문자열
        message: 상태에 대한 상세 메시지
    """
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "execution.log")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] [{status}] weekly_processor - {message}\n")


def parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱"""
    parser = argparse.ArgumentParser(
        description="주간 업무 로그를 요약해 Notion Weekly Achievements DB에 저장합니다."
    )
    parser.add_argument(
        "--start-date",
        dest="start_date",
        type=str,
        help="집계 시작일 (YYYY-MM-DD). 미지정 시 종료일 기준 6일 전.",
    )
    parser.add_argument(
        "--end-date", dest="end_date", type=str, help="집계 종료일 (YYYY-MM-DD). 기본값은 오늘."
    )
    parser.add_argument(
        "--status",
        dest="status_filter",
        type=str,
        default=None,
        help="특정 상태(Logged, Published 등)만 집계하고 싶을 때 사용.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Notion에 저장하지 않고 콘솔에 결과만 출력.",
    )
    return parser.parse_args()


def resolve_period(start_str: str | None, end_str: str | None) -> tuple[datetime, datetime]:
    """
    시작일과 종료일 문자열을 datetime으로 변환하고 기본값을 적용

    Args:
        start_str: 시작일 문자열
        end_str: 종료일 문자열

    Returns:
        (start_date, end_date) 튜플
    """
    today = datetime.now().date()

    if end_str:
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    else:
        end_date = today

    if start_str:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    else:
        start_date = end_date - timedelta(days=6)

    if start_date > end_date:
        raise ValueError("시작일은 종료일보다 이후일 수 없습니다.")

    return (
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.min.time()),
    )


class WeeklyProcessor:
    """주간 자동 요약 및 저장을 담당하는 클래스"""

    def __init__(
        self,
        notion_client: NotionClientWrapper | None = None,
        llm_client: BaseLLMClient | None = None,
    ):
        self.notion = notion_client or NotionClientWrapper()
        self.llm = llm_client or LLMClientFactory.create_client()

    def fetch_daily_logs(
        self, start_date: datetime, end_date: datetime, status_filter: str | None = None
    ) -> list[dict]:
        """
        지정된 기간의 일일 로그와 본문을 조회

        Args:
            start_date: 시작 시각
            end_date: 종료 시각
            status_filter: 상태 필터

        Returns:
            일일 로그 리스트
        """
        logs = self.notion.get_daily_logs_with_content(start_date, end_date, status_filter)
        return logs

    def summarize_logs(self, logs: list[dict]) -> dict:
        """
        LLM API를 사용해 일일 로그 묶음을 주간 성과로 요약

        Args:
            logs: 일일 로그 리스트

        Returns:
            bullet_points, key_highlights, raw_response를 포함한 dict
        """
        summary = self.llm.generate_weekly_summary(logs)
        return summary

    def save_weekly_summary(
        self, start_date: datetime, end_date: datetime, summary: dict, source_logs: list[dict]
    ) -> dict:
        """
        요약 결과를 Notion 주간 DB에 저장

        Args:
            start_date: 기간 시작일
            end_date: 기간 종료일
            summary: Claude 요약 결과
            source_logs: 일일 로그 원본

        Returns:
            생성된 페이지 객체
        """
        source_ids = [log["id"] for log in source_logs if "id" in log]
        page = self.notion.create_weekly_achievement(
            period_start=start_date,
            period_end=end_date,
            bullet_points=summary.get("bullet_points", ""),
            key_highlights=summary.get("key_highlights", ""),
            source_log_ids=source_ids,
        )
        return page

    def run(
        self,
        start_date: datetime,
        end_date: datetime,
        status_filter: str | None = None,
        dry_run: bool = False,
    ) -> dict | None:
        """
        주간 요약 전체 흐름 실행

        Args:
            start_date: 시작 시각
            end_date: 종료 시각
            status_filter: 상태 필터
            dry_run: Notion 저장 생략 여부

        Returns:
            저장된 페이지 객체 또는 None
        """
        write_execution_log("INFO", f"주간 처리 시작: {start_date.date()} ~ {end_date.date()}")
        logs = self.fetch_daily_logs(start_date, end_date, status_filter)

        if not logs:
            write_execution_log("INFO", "집계 기간에 해당하는 일일 로그가 없습니다.")
            return None

        summary = self.summarize_logs(logs)

        if dry_run:
            write_execution_log("INFO", "Dry-run 모드로 실행됨. Notion 저장을 건너뜁니다.")
            print("## 주간 성과 요약")
            print(summary.get("bullet_points", ""))
            print("\n## 핵심 하이라이트")
            print(summary.get("key_highlights", ""))
            return summary

        page = self.save_weekly_summary(start_date, end_date, summary, logs)
        write_execution_log("SUCCESS", f"주간 성과 저장 완료: {page.get('id')}")
        return page


def main():
    """CLI 엔트리 포인트"""
    args = parse_args()

    try:
        start_date, end_date = resolve_period(args.start_date, args.end_date)
    except ValueError as error:
        write_execution_log("ERROR", f"기간 해석 실패: {error}")
        print(f"기간 설정 오류: {error}")
        sys.exit(1)

    try:
        processor = WeeklyProcessor()
        processor.run(
            start_date=start_date,
            end_date=end_date,
            status_filter=args.status_filter,
            dry_run=args.dry_run,
        )
    except KeyboardInterrupt:
        write_execution_log("CANCELLED", "사용자가 Ctrl+C로 종료함")
        print("사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as error:
        write_execution_log("ERROR", f"주간 처리 실패: {error}")
        print(f"주간 자동 처리 중 오류가 발생했습니다: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
