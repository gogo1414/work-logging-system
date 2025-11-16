#!/usr/bin/env python3
"""
일일 업무 로거: Notion 일간 데이터베이스에 업무 기록을 남기는 대화형 CLI.

사용 예시:
    python scripts/daily_logger.py

별칭 설정 예시:
    alias daily-organize='python /절대경로/scripts/daily_logger.py'
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.utils.notion_client import NotionClientWrapper


class Colors:
    """터미널 출력을 위한 ANSI 색상 코드"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str):
    """구분선과 함께 헤더를 출력"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """성공 메시지를 출력"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """오류 메시지를 출력"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """안내 메시지를 출력"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def get_input(prompt: str, required: bool = True, default: str | None = None) -> str:
    """
    사용자 입력을 받고 기본값을 처리

    Args:
        prompt: 입력 안내 문구
        required: 필수 입력 여부
        default: 기본값

    Returns:
        최종 입력 문자열
    """
    if default:
        prompt_text = f"{Colors.OKBLUE}{prompt} [{default}]: {Colors.ENDC}"
    else:
        prompt_text = f"{Colors.OKBLUE}{prompt}: {Colors.ENDC}"

    while True:
        value = input(prompt_text).strip()

        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print_error("이 항목은 필수입니다. 값을 입력해주세요.")


def get_date_input(prompt: str, default: datetime | None = None) -> datetime:
    """
    날짜 입력을 받아 datetime 객체로 변환

    Args:
        prompt: 입력 안내 문구
        default: 기본 날짜 값

    Returns:
        YYYY-MM-DD 형태를 datetime으로 변환한 값
    """
    default_date = default or datetime.now()
    default_str = default_date.strftime("%Y-%m-%d")

    while True:
        value = get_input(prompt, default=default_str)
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            print_error(
                "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요."
            )


def get_multiline_input(prompt: str) -> str:
    """
    여러 줄 입력을 받아 하나의 문자열로 결합

    Args:
        prompt: 입력 안내 문구

    Returns:
        줄바꿈을 포함한 문자열
    """
    print(f"{Colors.OKBLUE}{prompt}")
    print(
        f"(여러 줄 입력 가능. 입력 완료 후 빈 줄에서 Enter를 두 번 누르세요){Colors.ENDC}\n"
    )

    lines = []
    empty_line_count = 0

    while True:
        line = input()

        if line.strip() == "":
            empty_line_count += 1
            if empty_line_count >= 2:
                break
            lines.append(line)
        else:
            empty_line_count = 0
            lines.append(line)

    return "\n".join(lines).strip()


def get_select_input(
    prompt: str, options: list[str], default: str | None = None
) -> str:
    """
    미리 정의된 선택지 중 하나를 고르는 함수

    Args:
        prompt: 입력 안내 문구
        options: 선택지 목록
        default: 기본 선택지

    Returns:
        선택된 옵션 문자열
    """
    print(f"\n{Colors.OKBLUE}{prompt}{Colors.ENDC}")
    for idx, option in enumerate(options, 1):
        default_marker = " (기본값)" if option == default else ""
        print(f"  {idx}. {option}{default_marker}")

    while True:
        choice = input(f"{Colors.OKBLUE}선택 (1-{len(options)}): {Colors.ENDC}").strip()

        if not choice and default:
            return default

        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(options):
                return options[choice_idx]
            else:
                print_error(f"1부터 {len(options)} 사이의 숫자를 입력해주세요.")
        except ValueError:
            print_error("숫자를 입력해주세요.")


def get_multi_select_input(prompt: str, options: list[str]) -> list[str]:
    """
    미리 정의된 선택지 중 여러 개를 고르는 함수

    Args:
        prompt: 입력 안내 문구
        options: 선택지 목록

    Returns:
        선택된 옵션 리스트
    """
    print(f"\n{Colors.OKBLUE}{prompt} (쉼표로 구분하여 여러 개 선택 가능){Colors.ENDC}")
    for idx, option in enumerate(options, 1):
        print(f"  {idx}. {option}")

    while True:
        choices = input(f"{Colors.OKBLUE}선택 (예: 1,3,5): {Colors.ENDC}").strip()

        if not choices:
            print_error("최소 1개 이상 선택해주세요.")
            continue

        try:
            selected_indices = [int(c.strip()) - 1 for c in choices.split(",")]
            selected_options = []

            for idx in selected_indices:
                if 0 <= idx < len(options):
                    selected_options.append(options[idx])
                else:
                    raise ValueError

            if selected_options:
                return selected_options
            else:
                print_error("올바른 선택지를 입력해주세요.")
        except ValueError:
            print_error("올바른 형식으로 입력해주세요 (예: 1,3,5).")


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
        log_file.write(f"[{timestamp}] [{status}] daily_logger - {message}\n")


def main():
    """일일 업무 로거의 메인 진입점"""
    print_header("📝 일일 업무 로거")
    print_info(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        notion = NotionClientWrapper()
        print_success("Notion API 연결 성공\n")
        write_execution_log("SUCCESS", "Notion API 인증 완료")
    except Exception as e:
        print_error(f"Notion API 연결 실패: {str(e)}")
        print_info("환경 변수(.env)가 올바르게 설정되었는지 확인해주세요.")
        write_execution_log("ERROR", f"Notion API 연결 실패: {str(e)}")
        sys.exit(1)

    print(f"{Colors.BOLD}업무 정보를 입력해주세요:{Colors.ENDC}\n")

    title = get_input("📌 업무 제목 (한 줄 요약)")

    logged_date = get_date_input("🗓️ 기록 날짜 (YYYY-MM-DD)")

    categories = ["성능개선", "신규기능", "버그픽스", "장애대응", "리팩토링", "기타"]
    category = get_select_input("📂 카테고리", categories)

    impact_levels = ["High", "Medium", "Low"]
    impact_level = get_select_input("⭐ 영향도", impact_levels)

    status_options = ["Logged", "In Review", "Published"]
    status = get_select_input("📌 상태", status_options, default="Logged")

    common_tech_stack = [
        "Python",
        "JavaScript",
        "TypeScript",
        "React",
        "Vue.js",
        "Node.js",
        "Django",
        "FastAPI",
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
        "Docker",
        "Kubernetes",
        "AWS",
        "GCP",
        "Git",
        "기타",
    ]
    print_info("자주 사용하는 기술 스택:")
    tech_stack_selections = get_multi_select_input("🛠️ 기술 스택", common_tech_stack)

    custom_tech = get_input(
        "🛠️ 추가 기술 스택 (쉼표로 구분, 없으면 Enter)", required=False
    )
    if custom_tech:
        tech_stack = tech_stack_selections + [t.strip() for t in custom_tech.split(",")]
    else:
        tech_stack = tech_stack_selections

    print()
    context = get_multiline_input("📝 상세 컨텍스트 (문제, 해결 과정, 결과)")

    metrics = get_input(
        "📊 정량적 지표 (예: 응답시간 50% 단축, DAU 10% 증가)", required=False
    )

    ticket_url = get_input("🔗 관련 이슈 URL (Jira, GitHub 등)", required=False)

    print_header("📋 입력 내용 확인")
    print(f"{Colors.BOLD}제목:{Colors.ENDC} {title}")
    print(f"{Colors.BOLD}기록 날짜:{Colors.ENDC} {logged_date.strftime('%Y-%m-%d')}")
    print(f"{Colors.BOLD}카테고리:{Colors.ENDC} {category}")
    print(f"{Colors.BOLD}영향도:{Colors.ENDC} {impact_level}")
    print(f"{Colors.BOLD}상태:{Colors.ENDC} {status}")
    print(f"{Colors.BOLD}기술 스택:{Colors.ENDC} {', '.join(tech_stack)}")
    print(f"{Colors.BOLD}정량 지표:{Colors.ENDC} {metrics if metrics else 'N/A'}")
    print(f"{Colors.BOLD}이슈 URL:{Colors.ENDC} {ticket_url if ticket_url else 'N/A'}")
    print(f"\n{Colors.BOLD}상세 컨텍스트:{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{context}{Colors.ENDC}\n")

    confirm = get_input("위 내용으로 저장하시겠습니까? (y/n)", default="y")

    if confirm.lower() not in ["y", "yes", "예", "ㅇ"]:
        print_info("취소되었습니다.")
        write_execution_log("CANCELLED", "사용자가 저장을 취소함")
        sys.exit(0)

    try:
        print_info("Notion에 저장 중...")

        page = notion.create_daily_log(
            title=title,
            context=context,
            category=category,
            impact_level=impact_level,
            tech_stack=tech_stack,
            logged_date=logged_date,
            status=status,
            metrics=metrics if metrics else None,
            ticket_url=ticket_url if ticket_url else None,
        )

        print_success("✨ Notion에 저장 완료!")
        print_info(f"페이지 URL: https://notion.so/{page['id'].replace('-', '')}")
        write_execution_log("SUCCESS", f"Notion 저장 완료: {page['id']}")

    except Exception as e:
        print_error(f"저장 실패: {str(e)}")
        write_execution_log("ERROR", f"Notion 저장 실패: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}작업이 취소되었습니다.{Colors.ENDC}")
        write_execution_log("CANCELLED", "사용자가 Ctrl+C로 종료함")
        sys.exit(0)
    except Exception as e:
        print_error(f"예상치 못한 오류 발생: {str(e)}")
        write_execution_log("ERROR", f"예상치 못한 오류: {str(e)}")
        sys.exit(1)
