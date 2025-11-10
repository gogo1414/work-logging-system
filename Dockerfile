# 베이스 이미지 선택 (slim으로 용량 최소화)
FROM python:3.11-slim

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 사전 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Python 모듈 탐색 경로 설정
ENV PYTHONPATH=/app

# FastAPI 서버 구동 (uvicorn)
CMD ["uvicorn", "scripts.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
