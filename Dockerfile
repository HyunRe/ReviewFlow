FROM public.ecr.aws/lambda/python:3.11

# 작업 디렉토리 설정
WORKDIR ${LAMBDA_TASK_ROOT}

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY main.py .

# 파이썬 경로 설정
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

# Lambda 진입점 지정 (main.py 파일의 handler 객체 호출)
CMD [ "main.handler" ]