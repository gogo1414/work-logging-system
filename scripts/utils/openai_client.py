"""
OpenAI ChatGPT API 클라이언트 구현
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

from .llm_client import BaseLLMClient

load_dotenv()


class OpenAIClient(BaseLLMClient):
    """OpenAI ChatGPT API 호출을 위한 클라이언트"""

    def __init__(self):
        """환경 변수에서 API 키를 읽어 OpenAI 클라이언트를 초기화"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # Latest GPT-4 Optimized model
        self.max_tokens = 2000

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
        from .prompts import WEEKLY_SUMMARY_SYSTEM_PROMPT, WEEKLY_SUMMARY_USER_TEMPLATE

        if system_prompt is None:
            system_prompt = WEEKLY_SUMMARY_SYSTEM_PROMPT

        # 프롬프트에 맞도록 일일 로그 포맷을 정리
        formatted_logs = self._format_daily_logs(daily_logs)

        user_prompt = WEEKLY_SUMMARY_USER_TEMPLATE.format(combined_logs=formatted_logs)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content

        parts = content.split("## 핵심 하이라이트")
        bullet_points = parts[0].replace("## 주간 성과 요약", "").strip()
        key_highlights = parts[1].strip() if len(parts) > 1 else ""

        if not bullet_points:
            bullet_points = content.strip()
        if not key_highlights:
            key_highlights = (
                "출력에서 핵심 하이라이트 구간을 찾지 못했습니다. 프롬프트를 확인해주세요."
            )

        return {
            "bullet_points": bullet_points,
            "key_highlights": key_highlights,
            "raw_response": content,
        }

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
        from .prompts import MONTHLY_SUMMARY_SYSTEM_PROMPT, MONTHLY_SUMMARY_USER_TEMPLATE

        if system_prompt is None:
            system_prompt = MONTHLY_SUMMARY_SYSTEM_PROMPT

        # 프롬프트에 맞도록 주간 성과 포맷을 정리
        formatted_weeks = self._format_weekly_achievements(weekly_achievements)

        user_prompt = MONTHLY_SUMMARY_USER_TEMPLATE.format(combined_weeks=formatted_weeks)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content

        parts = content.split("## 경력기술서용 요약")
        summary = parts[0].replace("## 월간 종합 성과", "").strip()
        career_brief = parts[1].strip() if len(parts) > 1 else ""

        if not summary:
            summary = content.strip()
        if not career_brief:
            career_brief = (
                "출력에서 경력기술서용 요약 구간을 찾지 못했습니다. 프롬프트를 확인해주세요."
            )

        return {"summary": summary, "career_brief": career_brief, "raw_response": content}
