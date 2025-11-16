"""
업무 기록 시스템을 위한 Notion API 래퍼 모듈
"""

import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv  # type: ignore[import]
from notion_client import Client  # type: ignore[import]

load_dotenv()


class NotionClientWrapper:
    """Notion API 작업을 편리하게 수행하기 위한 래퍼"""

    def __init__(self):
        """환경 변수에서 API 키를 읽어 Notion 클라이언트를 초기화"""
        self.api_key = os.getenv("NOTION_API_KEY")
        if not self.api_key:
            raise ValueError("NOTION_API_KEY not found in environment variables")

        self.client = Client(auth=self.api_key)  # type: ignore[call-arg]

        # 환경 변수에서 데이터베이스 ID를 읽어 저장
        self.daily_logs_db = os.getenv("NOTION_DB1_ID")  # Daily Work Logs
        self.weekly_db = os.getenv("NOTION_DB2_ID")  # Weekly Achievements
        self.monthly_db = os.getenv("NOTION_DB3_ID")  # Monthly Highlights

        if not self.daily_logs_db:
            raise ValueError("NOTION_DB1_ID not found in environment variables")

    def _parse_markdown_to_blocks(self, markdown_text: str) -> list[dict[str, Any]]:
        """
        마크다운 텍스트를 Notion 블록으로 변환

        Args:
            markdown_text: 마크다운 형식의 텍스트

        Returns:
            Notion 블록 리스트
        """
        blocks = []
        lines = markdown_text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # 빈 줄은 건너뛰기
            if not line.strip():
                i += 1
                continue

            # Heading 3 (###)
            if line.startswith("### "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line.replace("### ", "")}}
                            ]
                        },
                    }
                )
            # Heading 2 (##)
            elif line.startswith("## "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line.replace("## ", "")}}
                            ]
                        },
                    }
                )
            # Bulleted list (-)
            elif line.strip().startswith("- "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {"type": "text", "text": {"content": line.strip()[2:]}}
                            ]
                        },
                    }
                )
            # Numbered list (1., 2., etc.)
            elif line.strip() and line.strip()[0].isdigit() and ". " in line.strip()[:4]:
                content = line.strip().split(". ", 1)[1] if ". " in line.strip() else line.strip()
                blocks.append(
                    {
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": content}}]
                        },
                    }
                )
            # 일반 텍스트 (paragraph)
            else:
                # 여러 줄을 하나의 paragraph로 묶기
                paragraph_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip() and not lines[i].startswith(
                    ("#", "-", "1.", "2.", "3.", "4.")
                ):
                    paragraph_lines.append(lines[i])
                    i += 1
                i -= 1  # 다음 반복에서 올바른 라인부터 시작하도록 조정

                content = "\n".join(paragraph_lines)
                if content.strip():
                    blocks.append(
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": content}}]
                            },
                        }
                    )

            i += 1

        return blocks

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
    ) -> dict[str, Any]:
        """
        일일 업무 로그를 새로 생성

        Args:
            title: 업무 제목(한 줄 요약)
            context: 문제, 해결 과정, 결과를 포함한 상세 설명
            category: 업무 카테고리 (성능개선/신규기능 등)
            impact_level: 영향도 (High/Medium/Low)
            tech_stack: 사용한 기술 스택 리스트
            metrics: 정량 지표 (선택)
            ticket_url: 관련 이슈 URL (선택)

        Returns:
            생성된 페이지 객체
        """
        properties = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Logged Date": {"date": {"start": (logged_date or datetime.now()).isoformat()}},
            "Category": {"select": {"name": category}},
            "Impact Level": {"select": {"name": impact_level}},
            "Tech Stack": {"multi_select": [{"name": tech} for tech in tech_stack]},
            "Status": {"select": {"name": status or "Logged"}},
        }

        if metrics:
            properties["Metrics"] = {"rich_text": [{"text": {"content": metrics}}]}

        if ticket_url:
            properties["Ticket URL"] = {"url": ticket_url}

        # Context를 마크다운에서 Notion 블록으로 변환
        context_blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📝 상세 컨텍스트"}}]
                },
            }
        ]
        context_blocks.extend(self._parse_markdown_to_blocks(context))

        page = self.client.pages.create(
            parent={"database_id": self.daily_logs_db},
            properties=properties,
            children=context_blocks,
        )

        return page

    def get_daily_logs_with_content(
        self, start_date: datetime, end_date: datetime, status_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """
        지정된 기간 동안의 일일 로그를 조회하고 본문 콘텐츠를 함께 반환

        Args:
            start_date: 시작 날짜(포함)
            end_date: 종료 날짜(포함)
            status_filter: 상태 필터 (선택)

        Returns:
            properties와 content 키를 포함하는 로그 리스트
        """
        pages = self.get_daily_logs(start_date, end_date, status_filter)
        enriched_pages = []

        for page in pages:
            page_id = page.get("id")
            if not page_id:
                continue
            content = self.get_page_content(page_id)
            enriched_pages.append({**page, "content": content})

        return enriched_pages

    def get_daily_logs(
        self, start_date: datetime, end_date: datetime, status_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """
        특정 기간의 일일 로그를 조회

        Args:
            start_date: 시작 날짜(포함)
            end_date: 종료 날짜(포함)
            status_filter: 상태 필터 (선택)

        Returns:
            조건에 맞는 페이지 객체 리스트
        """
        filter_conditions = {
            "and": [
                {"property": "Logged Date", "date": {"on_or_after": start_date.isoformat()}},
                {"property": "Logged Date", "date": {"on_or_before": end_date.isoformat()}},
            ]
        }

        if status_filter:
            filter_conditions["and"].append(
                {"property": "Status", "select": {"equals": status_filter}}
            )

        results = self.client.databases.query(
            database_id=self.daily_logs_db,
            filter=filter_conditions,
            sorts=[{"property": "Logged Date", "direction": "ascending"}],
        )

        return results.get("results", [])

    def get_page_content(self, page_id: str) -> str:
        """
        Notion 페이지의 블록 콘텐츠를 문자열로 변환

        Args:
            page_id: Notion 페이지 ID

        Returns:
            페이지 내 텍스트 블록을 줄바꿈으로 이어 붙인 문자열
        """
        blocks = self.client.blocks.children.list(block_id=page_id)
        content_parts = []

        for block in blocks.get("results", []):
            block_type = block.get("type")
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                for text_obj in rich_text:
                    content_parts.append(text_obj.get("text", {}).get("content", ""))

        return "\n".join(content_parts)

    def update_log_status(self, page_id: str, status: str) -> dict[str, Any]:
        """
        일일 로그의 상태 값을 갱신

        Args:
            page_id: Notion 페이지 ID
            status: 바꿀 상태 값

        Returns:
            갱신된 페이지 객체
        """
        return self.client.pages.update(
            page_id=page_id, properties={"Status": {"select": {"name": status}}}
        )

    def create_weekly_achievement(
        self,
        period_start: datetime,
        period_end: datetime,
        bullet_points: str,
        key_highlights: str,
        source_log_ids: list[str],
    ) -> dict[str, Any]:
        """
        주간 성과 데이터를 생성해 DB에 저장

        Args:
            period_start: 주간 시작 날짜
            period_end: 주간 종료 날짜
            bullet_points: 이력서용 불릿 포인트
            key_highlights: 핵심 하이라이트 3줄 요약
            source_log_ids: 연관된 일일 로그 페이지 ID 리스트

        Returns:
            생성된 페이지 객체
        """
        if not self.weekly_db:
            raise ValueError("NOTION_DB2_ID not configured")

        title = f"{period_start.strftime('%Y년 %m월 %W주차')}"

        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "Period Start": {"date": {"start": period_start.isoformat()}},
            "Period End": {"date": {"start": period_end.isoformat()}},
            "Key Highlights": {"rich_text": [{"text": {"content": key_highlights}}]},
            "Generated At": {"date": {"start": datetime.now().isoformat()}},
            "Source Logs": {"relation": [{"id": log_id} for log_id in source_log_ids]},
        }

        page = self.client.pages.create(
            parent={"database_id": self.weekly_db},
            properties=properties,
            children=[
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "🎯 주간 성과 요약"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": bullet_points}}]
                    },
                },
            ],
        )

        return page

    def get_weekly_achievements_with_content(
        self, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """
        주어진 기간의 주간 성과 페이지와 본문을 조회

        Args:
            start_date: 시작 날짜(포함)
            end_date: 종료 날짜(포함)

        Returns:
            properties와 content 키를 포함한 주간 성과 리스트
        """
        if not self.weekly_db:
            raise ValueError("NOTION_DB2_ID not configured")

        filter_conditions = {
            "and": [
                {"property": "Period Start", "date": {"on_or_after": start_date.isoformat()}},
                {"property": "Period End", "date": {"on_or_before": end_date.isoformat()}},
            ]
        }

        results = self.client.databases.query(
            database_id=self.weekly_db,
            filter=filter_conditions,
            sorts=[{"property": "Period Start", "direction": "ascending"}],
        )

        enriched_pages = []
        for page in results.get("results", []):
            page_id = page.get("id")
            if not page_id:
                continue
            content = self.get_page_content(page_id)
            enriched_pages.append({**page, "content": content})

        return enriched_pages

    def create_monthly_highlight(
        self,
        year: int,
        month: int,
        summary: str,
        career_brief: str,
        source_week_ids: list[str],
        stats_text: str,
    ) -> dict[str, Any]:
        """
        월간 하이라이트 데이터를 생성해 DB에 저장

        Args:
            year: 연도
            month: 월
            summary: 월간 종합 성과 본문
            career_brief: 경력기술서용 요약
            source_week_ids: 연관된 주간 성과 페이지 ID 리스트
            stats_text: 통계 요약 문자열

        Returns:
            생성된 페이지 객체
        """
        if not self.monthly_db:
            raise ValueError("NOTION_DB3_ID not configured")

        title = f"{year}년 {month:02d}월"
        year_month_date = datetime(year=year, month=month, day=1)

        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "Year-Month": {"date": {"start": year_month_date.isoformat()}},
            "Generated At": {"date": {"start": datetime.now().isoformat()}},
            "Source Weeks": {"relation": [{"id": week_id} for week_id in source_week_ids]},
            "Stats": {"rich_text": [{"text": {"content": stats_text}}]},
        }

        page = self.client.pages.create(
            parent={"database_id": self.monthly_db},
            properties=properties,
            children=[
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "📈 월간 종합 성과"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]},
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "🧾 경력기술서용 요약"}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": career_brief}}]
                    },
                },
            ],
        )

        return page
