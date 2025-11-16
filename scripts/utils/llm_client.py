"""
LLM 클라이언트 추상 기본 클래스 및 Factory 패턴 구현
"""

import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()


class BaseLLMClient(ABC):
    """모든 LLM 클라이언트가 상속해야 하는 추상 기본 클래스"""

    @abstractmethod
    def generate_weekly_summary(
        self, daily_logs: list[dict], system_prompt: str | None = None
    ) -> dict[str, str]:
        """
        일일 로그 묶음을 기반으로 주간 성과 요약을 생성

        Args:
            daily_logs: 속성과 본문을 포함한 일일 로그 리스트
            system_prompt: 커스텀 시스템 프롬프트 (선택, 미지정 시 기본값 사용)

        Returns:
            bullet_points, key_highlights, raw_response를 포함한 딕셔너리
        """
        pass

    @abstractmethod
    def generate_monthly_summary(
        self, weekly_achievements: list[dict], system_prompt: str | None = None
    ) -> dict[str, str]:
        """
        주간 성과 묶음을 기반으로 월간 하이라이트를 생성

        Args:
            weekly_achievements: 주간 성과 엔트리 리스트
            system_prompt: 커스텀 시스템 프롬프트 (선택)

        Returns:
            summary, career_brief, raw_response를 포함한 딕셔너리
        """
        pass

    def _format_daily_logs(self, daily_logs: list[dict]) -> str:
        """일일 로그를 프롬프트용 문자열로 변환 (공통 로직)"""
        formatted_parts = []

        for idx, log in enumerate(daily_logs, 1):
            props = log.get("properties", {})

            title_prop = props.get("Title", {})
            title = ""
            if title_prop.get("title"):
                title = title_prop["title"][0].get("text", {}).get("content", "")

            category = props.get("Category", {}).get("select", {}).get("name", "")

            impact = props.get("Impact Level", {}).get("select", {}).get("name", "")

            tech_stack = props.get("Tech Stack", {}).get("multi_select", [])
            tech_names = [tech.get("name", "") for tech in tech_stack]

            metrics_prop = props.get("Metrics", {}).get("rich_text", [])
            metrics = ""
            if metrics_prop:
                metrics = metrics_prop[0].get("text", {}).get("content", "")

            context = log.get("content", "")

            formatted_parts.append(
                f"""
### 로그 {idx}: {title}
- **카테고리**: {category}
- **영향도**: {impact}
- **기술 스택**: {', '.join(tech_names)}
- **정량 지표**: {metrics if metrics else 'N/A'}

**상세 컨텍스트**:
{context}
---
"""
            )

        return "\n".join(formatted_parts)

    def _format_weekly_achievements(self, weekly_achievements: list[dict]) -> str:
        """주간 성과 데이터를 프롬프트용 문자열로 변환 (공통 로직)"""
        formatted_parts = []

        for idx, week in enumerate(weekly_achievements, 1):
            props = week.get("properties", {})

            title_prop = props.get("Title", {})
            title = ""
            if title_prop.get("title"):
                title = title_prop["title"][0].get("text", {}).get("content", "")

            highlights_prop = props.get("Key Highlights", {}).get("rich_text", [])
            highlights = ""
            if highlights_prop:
                highlights = highlights_prop[0].get("text", {}).get("content", "")

            bullet_points = week.get("content", "")

            formatted_parts.append(
                f"""
### {title}
**핵심 하이라이트**: {highlights}

**주간 성과**:
{bullet_points}
---
"""
            )

        return "\n".join(formatted_parts)


class LLMClientFactory:
    """LLM 클라이언트 인스턴스를 생성하는 Factory"""

    @staticmethod
    def create_client(provider: str | None = None) -> BaseLLMClient:
        """
        환경 변수 또는 명시적 provider 값을 기반으로 LLM 클라이언트 생성

        Args:
            provider: LLM 제공자 ('claude', 'openai', 'gemini'). None이면 환경 변수 참조

        Returns:
            BaseLLMClient 인스턴스

        Raises:
            ValueError: 지원하지 않는 provider
        """
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "claude").lower()

        if provider == "claude":
            from .claude_client import ClaudeClientWrapper

            return ClaudeClientWrapper()
        elif provider == "openai":
            from .openai_client import OpenAIClient

            return OpenAIClient()
        elif provider == "gemini":
            from .gemini_client import GeminiClient

            return GeminiClient()
        else:
            raise ValueError(
                f"지원하지 않는 LLM 제공자: {provider}. "
                f"'claude', 'openai', 'gemini' 중 하나를 선택하세요."
            )
